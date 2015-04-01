#!/usr/bin/env python
#coding:utf8
# Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-26 13:16:10
# Filename        : cyclone/http.py
# Description     : 
from cyclone.config import CRLF
from cyclone.e import HeaderFormatError
from cyclone.utils import urlsplit, urldecode 
from cyclone.socket import IOSocket
from cyclone.config import CRLF
from time import time

class HTTPConnection(IOSocket):
    def parse_request_all(self):
        """从原始数据中提取头信息"""
        _headers, _body  = self._request_data.split(CRLF * 2, 1)
        _first_line, _headers = _headers.split(CRLF, 1)
        return _first_line, _headers, _body
    
    def send_headers(self, headers_string):
        """headers_string是已经被处理过了的头信息，直接写入就行"""
        self.send_string(headers_string)

    def send_body(self, body_string):
        """同send_headers"""
        self.send_string(body_string)

    def remote_ip(self):
        return self._socket.getpeername()[0]

class HTTPRequest():
    def __init__(self, method, uri, version, headers, body, connection, real_ip = True):
        self.method = method
        self.uri = uri
        self.version = version
        self.headers = headers
        self.body = body
        _urlparse = urlsplit(self.uri)
        self.path = _urlparse.path
        self.query = _urlparse.query
        self.connection = connection
        self._start_time = time()
        self.real_ip = real_ip

    @property
    def client_ip(self):
        if self.real_ip:
            _remote_ip = self.headers.get("X-Real-IP", 
                self.headers.get("X-Forwarded-For", self.connection.remote_ip()))
        else:
            _remote_ip = self.connection.remote_ip()

        return _remote_ip

    @property
    def request_time(self):
        return time() - self._start_time

    @property
    def query_arguments(self):
        return urldecode(self.query)

    @property
    def body_arguments(self):
        return urldecode(self.body)

    @property
    def all_arguments(self):
        return urldecode("&".join(filter(bool, [self.body, self.query]))) # filter是为了将空白去掉

class HTTPHeaders(dict):
    def __init__(self, headers=None):
        headers = headers or {}

        if not isinstance(headers, dict):
            headers = self.__parse_headers(headers)

        for _k, _v in headers.items():
            self[_k] = _v

    def __parse_headers(self, headers):
        """把http头信息组织到一个字典中去"""
        _headers = {}
        assert not isinstance(headers, dict)
        for header_line in headers.split(CRLF):
            if ':' not in header_line: # 如果':' 不在某一条header中，则表示这个 header有错的
                raise HeaderFormatError 
            _header_name, _header_value = header_line.split(':', 1)
            _headers[_header_name] = _header_value

        return _headers

    def get_response_headers_string(self, first_line):
        """生成响应头，并加上最后的两个CRLF"""
        _headers_string = first_line
        for _name, _value in self.items():
            _header_line = "{name}: {value}".format(
                    name = _name, value = _value)
            _headers_string += (CRLF + _header_line)

        return _headers_string + CRLF * 2

def get_request(socket, real_ip=True):
    """在刚连接时，获取用户的http请求信息"""
    connection = HTTPConnection(socket)
    _first_line, _headers, _body = connection.parse_request_all() # 把收到的信息分析出来
    headers = HTTPHeaders(_headers) # 这是http headers信息，类型是dict
    method , uri, version = map(lambda s: s.strip(), _first_line.split())

    return HTTPRequest(method = method, uri = uri, version = version,
            headers = headers, body = _body, connection = connection, real_ip = real_ip)

