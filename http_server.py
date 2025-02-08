#!/usr/bin/python
# HTTP文件服务器程序，用于客户端上传和管理服务器中的文件
# 本地测试启动 python HTTP_server.py 8000
# 支持linux服务器启动

# 忽略挂断信号 , 默认端口80
# nohup python3 HTTP_SERVER.py >> ../HTTP_SERVER.log 2>&1 &

__version__ = "1.0.1"
#__author__ = "antrn CSDN: https://blog.csdn.net/qq_38232598" # 原作者
__all__ = ["HTTPFileRequestHandler"]

import os,time,sys,re,shutil,_thread,webbrowser
import socket
import posixpath
try:
    from html import escape
except ImportError:
    from cgi import escape
import mimetypes
import signal
from io import BytesIO
import codecs

from urllib.parse import quote
from urllib.parse import unquote
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler


class HTTPFileRequestHandler(BaseHTTPRequestHandler):

    server_version = "Python HTTP File Server/" + __version__
    IPAddress = socket.gethostbyname(socket.gethostname())

    def getAllFilesList(self):
        listofme = []
        for root, dirs, files in os.walk(translate_path(self.path)):
            files.sort()
            for fi in files:
                display_name = os.path.join(root, fi)
                # 删除前面的n个字符，取出相对当前目录的路径
                relative_path = display_name[len(
                    os.getcwd()):].replace('\\', '/')[1:]
                if not relative_path.startswith('.'):
                    # print("display", display_name)
                    st = os.stat(display_name)
                    # fsize = st.st_size
                    fsize = bytes_conversion(display_name)
                    #print("Size", str(os.path.getsize(display_name)))
                    fmtime = time.strftime(
                        '%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime))
                    listofme.append(relative_path+"\t")
                    listofme.append(fsize+"\t")
                    listofme.append(str(fmtime)+"\t\n")
        return listofme

    def calculate_dir_size(self, pathvar):
        '''
        calculate dir size(bytes)
        '''
        size = 0
        try:
            lst = os.listdir(pathvar)
            for i in lst:
                pathnew = os.path.join(pathvar, i)
                if os.path.isfile(pathnew):
                    size += os.path.getsize(pathnew)
                elif os.path.isdir(pathnew):
                    size += self.calculate_dir_size(pathnew)
        except OSError as err:
            print("文件访问错误：%s (%s)" % (type(err).__name__,str(err)))
        return size

    # 程序中GET/HEAD/POST请求完全相同，只是HEAD请求忽略了文件的实际内容。
    def do_GET(self):
        """Serve a GET request."""
        paths = unquote(self.path)
        path = str(paths)
        print("访问路径：", path)
        plist = path.split("/", 2)
        if len(plist) > 2 and plist[1] == "delete":
            result = plist[2]
            #print("确认删除文件/目录：", result)
            if result.startswith("/"):
                result = result[1:]
            if os.path.exists(result):
                print("删除文件/目录：", result)
                # dirn = os.path.dirname(result)
                if os.path.isdir(result):
                    shutil.rmtree(result)
                else:
                    os.remove(result)
                # 删除完文件，检测是否为空，删除文件夹
                # print("Parent Directory", dirn)
                # if dirn != '' and not os.listdir(dirn):
                #     os.removedirs(dirn)
                time.sleep(0.5)
                # 0.5s后重定向
                self.send_response(302)
                self.send_header('Location', "/")
                self.end_headers()
                return

        # 这个一定要放在后面，否则，怎么都不会重定向，一直卡在默认的404页面
        fd = self.send_head()
        if fd:
            shutil.copyfileobj(fd, self.wfile)
            fd.close()
        # 查看当前的请求路径
        # 参考https://blog.csdn.net/qq_35038500/article/details/87943004

    def do_HEAD(self):
        """Serve a HEAD request."""
        fd = self.send_head()
        if fd:fd.close()

    def do_POST(self):
        """Serve a POST request."""
        r, info = self.deal_post_data()

        f = BytesIO()
        f.write(b'<!DOCTYPE html>')
        f.write("<html>\n<head><title>上传结果页面</title></head>\n".encode())
        f.write("<body>\n<h2>上传结果页面</h2>\n".encode())
        f.write(b"<hr>\n")
        if r:
            f.write("<strong>上传成功:</strong><br>".encode())
        else:
            f.write("<strong>上传失败:</strong><br>".encode())

        for i in info:
            #print(r, i, "by: ", self.client_address)
            f.write(i.encode('utf-8')+b"<br>")
        f.write(("<br><a href=\"%s\">返回</a>" % self.headers['referer']).encode())
        #f.write(b"<hr><small>Powered By: freelamb, check new version at ")
        #f.write(b"<a href=\"https://github.com/freelamb/simple_http_server\">")
        f.write(b"</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html;charset=utf-8")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        if f:
            shutil.copyfileobj(f, self.wfile)
            f.close()

    def str_to_chinese(self, var):
        not_end = True
        while not_end:
            start1 = var.find("\\x")
            # print(start1)
            if start1 > -1:
                str1 = var[start1 + 2:start1 + 4]
                #print(str1)
                start2 = var[start1 + 4:].find("\\x") + start1 + 4
                if start2 > -1:
                    str2 = var[start2 + 2:start2 + 4]

                    start3 = var[start2 + 4:].find("\\x") + start2 + 4
                    if start3 > -1:
                        str3 = var[start3 + 2:start3 + 4]
            else:
                not_end = False
            if start1 > -1 and start2 > -1 and start3 > -1:
                str_all = str1 + str2 + str3
                # print(str_all)
                str_all = codecs.decode(str_all, "hex").decode('utf-8')

                str_re = var[start1:start3 + 4]
                # print(str_all, "   " ,str_re)
                var = var.replace(str_re, str_all)
        # print(var.decode('utf-8'))
        return var

    def deal_post_data(self):
        boundary = self.headers["Content-Type"].split("=")[1].encode('ascii')
        #print("boundary===", boundary)
        remain_bytes = int(self.headers['content-length'])
        #print("remain_bytes===", remain_bytes)

        res = []
        line = self.rfile.readline()
        while boundary in line and str(line, encoding="utf-8")[-4:] != "--\r\n":

            # line = self.rfile.readline()
            remain_bytes -= len(line)
            if boundary not in line:
                return False, ["Content NOT begin with boundary"]
            line = self.rfile.readline()
            remain_bytes -= len(line)
            #print("line!!!", line)
            fn = re.findall(
                r'Content-Disposition.*name="file"; filename="(.*)"', str(line))
            if not fn or not fn[0]:
                print("上传失败，用户未选择文件路径")
                return False, ["请先选择文件或文件夹！"]
            path = translate_path(self.path)

            fname = fn[0]
            # fname = fname.replace("\\", "\\\\")
            fname = self.str_to_chinese(fname)
            print("上传文件：", fname)

            fn = os.path.join(path, fname)
            if os.path.exists(fn): # 文件已存在
                i = 1
                filename,ext = os.path.splitext(fn)
                fn = filename + " - 新上传(%d)"%i + ext
                while os.path.exists(fn):
                    i += 1
                    fn = filename + " - 新上传(%d)"%i + ext

            dirname = os.path.dirname(fn)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            line = self.rfile.readline()
            remain_bytes -= len(line)
            line = self.rfile.readline()
            # b'\r\n'
            remain_bytes -= len(line)
            try:
                out = open(fn, 'wb')
            except IOError:
                print("服务器写入文件失败：%s" % fn)
                return False, ["上传失败，服务器可能没有权限写入文件。"]

            pre_line = self.rfile.readline()
            #print("pre_line", pre_line)
            remain_bytes -= len(pre_line)
            #print("remain_bytes", remain_bytes)
            Flag = True
            while remain_bytes > 0:
                line = self.rfile.readline()
                #print("while line", line)

                if boundary in line:
                    remain_bytes -= len(line)
                    pre_line = pre_line[0:-1]
                    if pre_line.endswith(b'\r'):
                        pre_line = pre_line[0:-1]
                    out.write(pre_line)
                    out.close()
                    # return True, "File '%s' upload success!" % fn
                    res.append("成功上传文件 %s !" % fn)
                    Flag = False
                    break
                else:
                    out.write(pre_line)
                    pre_line = line
            if pre_line is not None and Flag == True:
                out.write(pre_line)
                out.close()
                res.append("成功上传文件 %s !" % fn)
        # return False, "Unexpect Ends of data."
        return True, res

    def send_head(self):
        """Common code for GET and HEAD commands.
        This sends the response code and MIME headers.
        Return value is either a file object (which has to be copied
        to the output file by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.
        """
        path = translate_path(self.path)
        if os.path.isdir(path):
            if not self.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None
            for index in ("index.html","index.htm","index.mht"):
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        content_type = self.guess_type(path)
        try:
            # Always read in binary mode. Opening files in text mode may cause
            # newline translations, making the actual size of the content
            # transmitted *less* than the content-length!
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None
        self.send_response(200)
        # self.send_header("Content-type", content_type)
        # Fix Messy Display
        self.send_header("Content-type", content_type+";charset=utf-8")
        fs = os.fstat(f.fileno())
        self.send_header("Content-Length", str(fs[6]))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f

    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).
        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().
        """
        try:
            list_dir = os.listdir(path)
        except OSError:
            self.send_error(404, "No permission to list the directory")
            return None
        f = BytesIO()
        display_path = escape(unquote(self.path))
        f.write(b'<!DOCTYPE html>')
        f.write(("<html>\n<head><title>%s 的目录</title></head>\n" %
                display_path).encode('utf-8'))
        f.write(("<body>\n<h2>路径 %s 的目录</h2>\n" %
                display_path).encode('utf-8'))
        f.write(b"<hr>\n")
        # 上传目录
        f.write("<h3>上传文件夹</h3>\n".encode())
        f.write(b"<form ENCTYPE=\"multipart/form-data\" method=\"post\">")
        # @change=\"handleChange\" @click=\"handelClick\"
        f.write(
            b"<input ref=\"input\" webkitdirectory multiple name=\"file\" type=\"file\"/>")
        f.write("<input type=\"submit\" value=\"上传\"/></form>\n".encode())
        f.write(b"<hr>\n")
        # 上传文件
        f.write("<h3>上传文件</h3>\n".encode())
        f.write(b"<form ENCTYPE=\"multipart/form-data\" method=\"post\">")
        f.write(b"<input ref=\"input\" multiple name=\"file\" type=\"file\"/>")
        f.write("<input type=\"submit\" value=\"上传\"/></form>\n".encode())

        f.write(b"<hr>\n")
        # 表格
        f.write(b"<table with=\"100%\" style='text-align:center'>")
        f.write("<tr><th>路径</th>".encode())
        f.write("<th>类型</th>".encode())
        f.write("<th>大小</th>".encode())
        f.write("<th>修改时间</th>".encode())
        f.write("<th>操作</th>".encode())
        f.write(b"</tr>")

        files=[];dirs=[];links=[]
        # 根目录下所有的内容
        for name in list_dir:
            #if name.startswith('.'):continue
            fullname = os.path.join(path, name)
            if os.path.isdir(fullname):# 如果是文件夹
                dirs.append(name)
            elif os.path.islink(fullname):# 如果是链接文件
                links.append(name)
            else:
                files.append(name)
        key=lambda a:a.lower() # 忽略大小写
        files.sort(key=key);dirs.sort(key=key);links.sort(key=key) # 按名称升序排序

        if self.path != "/":
            f.write('<tr><td><a href="..">&nbsp;&nbsp;..&nbsp;&nbsp;</a></td>'.encode('utf-8'))
            f.write('<td>(上层目录)</td></tr>'.encode('utf-8'))
        for name in dirs:
            fullname = os.path.join(path, name) # 根目录下的路径
            st = os.stat(fullname)

            #fsize = bytes_conversion(
            #    "", self.calculate_dir_size(fullname)) # 为避免影响性能，不计算文件夹的大小
            fmtime = time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime))
            relative_path = fullname[len(
                os.getcwd()):].replace('\\', '/')
            f.write(b"<tr>")
            f.write(b'<td><a href="%s">%s</a></td>' % (
                ("/"+relative_path).encode('utf-8'), escape("/"+name).encode('utf-8')))
            if os.path.isdir(fullname):
                ftype = "文件夹"
            else:
                ftype = "文件"
            f.write(b"<td>%s</td>" %
                    escape(ftype).encode('utf-8'))
            f.write(b"<td></td>")
            #f.write(b"<td>%s</td>" %
            #        escape(fsize).encode('utf-8'))
            f.write(b"<td>%s</td>" %
                    escape(fmtime).encode('utf-8'))
            f.write(("<td><a style='border: solid 1px red; text-decoration: none; background: red; color: white;' href=\"/delete/%s\">删除</a>" %
                    fullname).encode('utf-8'))
            f.write(b"</tr>")
        for name in links:
            linkname = name + "/"
            #print("real link name ===", linkname)
            name += "@"
            # Note: a link to a directory displays with @ and links with /
            f.write(b'<li><a href="%s">%s</a>\n' %
                    (quote(linkname).encode('utf-8'), escape(name).encode('utf-8')))
        for name in files:
            fullname = os.path.join(path, name) # 根目录下的路径
            # 其他直接在根目录下的文件，直接显示出来
            st = os.stat(fullname)
            # fsize = st.st_size
            fsize = bytes_conversion(fullname)
            fmtime = time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime))
            f.write(b"<tr>")
            f.write(b'<td><a href="%s">%s</a></td>' %
                    (quote(name).encode('utf-8'), escape(name).encode('utf-8')))
            if os.path.isdir(fullname):
                ftype = "文件夹"
            else:
                ftype = "文件"
            f.write(b"<td>%s</td>" %
                    escape(ftype).encode('utf-8'))
            f.write(b"<td>%s</td>" % escape(fsize).encode('utf-8'))
            f.write(b"<td>%s</td>" % escape(fmtime).encode('utf-8'))
            f.write(("<td><a href=\"/delete/%s\">删除</a>" %
                    escape(fullname)).encode('utf-8'))
            f.write(b"</tr>")

        f.write(b"</table>")
        f.write(b"\n<hr>\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html;charset=utf-8")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

    def guess_type(self, path):
        """Guess the type of a file.
        Argument is a PATH (a filename).
        Return value is a string of the form type/subtype,
        usable for a MIME Content-type header.
        The default implementation looks the file's extension
        up in the table self.extensions_map, using application/octet-stream
        as a default; however it would be permissible (if
        slow) to look inside the data to make a better guess.
        """

        base, ext = posixpath.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        else:
            return self.extensions_map['']

    if not mimetypes.inited:
        mimetypes.init()  # try to read system mime.types
    extensions_map = mimetypes.types_map.copy()
    extensions_map.update({
        '': 'application/octet-stream',  # 默认
        '.py': 'text/plain',
        '.txt': 'text/plain',
        ".htm": "text/html", ".html": "text/html",
        ".css": "text/css",
        ".js": "application/javascript", ".ts": "application/javascript",
    })


def translate_path(path):
    """Translate a /-separated PATH to the local filename syntax.
    Components that mean special things to the local file system
    (e.g. drive or directory names) are ignored.  (XXX They should
    probably be diagnosed.)
    """
    # abandon query parameters
    path = path.split('?', 1)[0]
    path = path.split('#', 1)[0]
    path = posixpath.normpath(unquote(path))
    words = path.split('/')
    words = filter(None, words)
    path = os.getcwd()
    for word in words:
        drive, word = os.path.splitdrive(word)
        head, word = os.path.split(word)
        if word in (os.curdir, os.pardir):
            continue
        path = os.path.join(path, word)
    return path


def bytes_conversion(file_path, total_size=-1):
    """
    calculate file size and dynamically convert it to K, M, GB, etc.
    :param file_path:
    :param total_size: the size of a dir
    :return: file size with format
    """
    number = 0
    if total_size == -1:
        number = os.path.getsize(file_path)
    else:
        number = total_size
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = dict()
    for a, s in enumerate(symbols):
        prefix[s] = 1 << (a + 1) * 10
    for s in reversed(symbols):
        if int(number) >= prefix[s]:
            value = float(number) / prefix[s]
            return '%.2f%s' % (value, s)
    return "%sB" % number


def signal_handler(signal, frame):
    print("您选择关闭服务器")
    exit()

def auto_open(port,delay=0.5):
    time.sleep(delay)
    webbrowser.open('http://127.0.0.1:%d/'%port)
def main():
    if sys.argv[1:]:
        port = int(sys.argv[1])
    else:
        port = 80 # http的默认端口，选择80后在URL中可不加端口号。(也可改成其他端口)
    server_address = ('', port)
    _thread.start_new_thread(auto_open,(port,))

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    httpd = HTTPServer(server_address, HTTPFileRequestHandler)
    
    host_name = socket.gethostname()
    ip = socket.gethostbyname(host_name)
    server = httpd.socket.getsockname()
    print("服务器版本: " + HTTPFileRequestHandler.server_version +
          ", Python版本: " + HTTPFileRequestHandler.sys_version)
    print("服务器IP地址: %s 端口: %s" % (ip, str(server[1]))) # 不使用server[0]作为ip地址，这一项一般是0.0.0.0
    httpd.serve_forever()

if __name__ == '__main__':
    main()
