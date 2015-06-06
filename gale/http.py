#!/usr/bin/env python
#coding:utf8
# Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-26 13:16:10
# Filename        : gale/http.py
# Description     : 
from gale.config import CRLF
from gale.e import HeaderFormatError, NotSupportHttpVersion
from gale.utils import urlsplit, urldecode
from gale.iosocket import IOSocket
from gale.log import gen_log
from gevent import socket
import traceback
from time import time
import re

class HTTPConnection(IOSocket):
    def parse_request_headers(self):
        """从原始数据中提取头信息"""
        _first_line, _headers = (self._headers.split(CRLF, 1) +  [''])[:2]
        return _first_line, _headers

    def read_body(self, max_length):
        if max_length == 0: # 如果请求headers中没有指定 Content-Type或者为0,表示没有请求主体
            return ''

        body = self._buff # _buff里的内容是在读取 headers时多读取的数据
        while len(body) < max_length:
            _body_data = self._socket.recv(self.max_buff)
            if not _body_data:
                break
            body += _body_data

        return body

    def read_headers(self):
        eof = -1
        _headers = ''
        while True:
            _data = self._socket.recv(self.max_buff)
            if not _data:
                break
            self._buff += _data
            eof = self._buff.find(CRLF * 2)
            if eof != -1:
                _headers, self._buff = self._buff[:eof], self._buff[eof + len(CRLF * 2):]
                break

        return _headers.strip()

    def get_request(self, callback):
        """获取用户的请求信息，并可以成功取得一个http请求时，生成一个HTTPRequest, 并激活回调函数(application的__call__)"""
        while True and self.closed == False:
            try:
                _headers = self.read_headers()
            except socket.timeout: # socket超时的异步不报出
                _headers = None

            if not _headers:
                self.close()
                break

            self._headers = _headers
            del _headers
            request = get_request(self)
            callback(request)

    def send_headers(self, headers_string):
        """headers_string是已经被处理过了的头信息，直接写入就行"""
        self.send_string(headers_string)

    def send_body(self, body_string):
        """同send_headers"""
        self.send_string(body_string)

        self.send_string(CRLF)

    def remote_ip(self):
        return self._socket.getpeername()[0]

class HTTPRequest():
    def __init__(self, method, uri, version, headers, body, connection, real_ip = True):
        self.method = method
        self.uri = uri
        self.version = version
        self.version_num = self.__version_num() 
        self.headers = headers
        self.body = body
        _urlparse = urlsplit(self.uri)
        self.path = _urlparse.path
        self.host = headers.get('Host', '').strip()
        self.query = _urlparse.query
        self.connection = connection
        self._start_time = time()
        self.real_ip = real_ip
        self.cookies = self.__get_cookies()
        self.files = {}
        self._body_arguments = {}

    def _parse_body(self):
        content_type = self.headers.get('Content-Type', '')

        if content_type.startswith('multipart/form-data'):
            parse_multipart_form_data(content_type, self.body, args = self._body_arguments,
                    files = self.files)
        else:
            self._body_arguments = urldecode(self.body) 

    def __get_cookies(self):
        _cookies = {}
        _cookies_string = self.headers.get('Cookie', '')
        if not _cookies_string:
            return {}

        _cookies_list = [_cookie_string.split('=', 1) for _cookie_string in  _cookies_string.split(';')]
        for _cookie_name, _cookie_value in _cookies_list:
            _cookies[_cookie_name.strip()] = _cookie_value.strip()

        return _cookies

    def __version_num(self):
        _version_num = self.version.split('/', 1)[1]
        if not re.match(r'^1\.[01]$', _version_num):
            raise NotSupportHttpVersion

        return _version_num

    def is_keep_alive(self):
        _connection_param = self.headers.get('Connection', '').lower()
        if _connection_param:
            return _connection_param.lower() != 'close'

        if self.version_num == '1.1': # 如果http版本是1.1默认是保持连接的
            return True

        return False

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
        return self._body_arguments

    @property
    def all_arguments(self):
        _args = {}
        _args.update(self.query_arguments)
        _args.update(self.body_arguments)
        return _args

class HTTPHeaders(dict):
    def __init__(self, headers=None):
        dict.__init__(self)
        headers = headers or {}
        self._headers_map_list = {} # 数据格式: {name: [value1, value2,...]}

        if not isinstance(headers, dict): # 如果传入的headers不是字典，表示这是请求headers，则调用dict原有的__setitem__ 将头信息传进去，如果传入是dict，则表示是响应头，则需要处理一下，比如同域名的，但是不同域值要放一块
            headers = self._parse_headers(headers)
            for _k, _v in headers.items():
                dict.__setitem__(self, _k, _v)

        for _k, _v in headers.items():
            self[_k] = _v


    @staticmethod
    def _parse_headers(headers):
        """把http头信息组织到一个字典中去"""
        _headers = {}
        _last_key = None
        assert not isinstance(headers, dict)
        for header_line in headers.split('\n'):
            header_line = header_line.rstrip('\r')
            if header_line.startswith('\x20') or header_line.startswith('\t') :  # 因为http首部是允许换行的, 所以如果这一行是以空格或制表符开头的，需要将信息加到之前那行
                _headers[_last_key] += ' ' + header_line.lstrip()
                continue
            else:
                _header_name, _header_value = header_line.split(':', 1)
            _headers[_header_name] = _header_value.strip()
            _last_key = _header_name

        return _headers

    def get_response_headers_string(self, first_line):
        """生成响应头，并加上最后的两个CRLF"""
        _headers_string = first_line
        for _name, _value_list in self._headers_map_list.items():
            for _value in _value_list:
                _header_line = "{name}: {value}".format(
                    name = _name, value = _value)
                _headers_string += (CRLF + _header_line)


        return _headers_string + CRLF * 2

    def __setitem__(self, name, value):
        self._headers_map_list[name] = [value]

    def __getitem__(self, name):
        if name in self._headers_map_list:
            return self._headers_map_list[name][0]
        else:
            raise KeyError

    def add(self, name, value):
        self._headers_map_list.setdefault(name, []).append(value)


class HTTPFile(object):
    def __init__(self, filename, body, content_type):
        self.filename = filename
        self.body = body
        self.content_type = content_type

    def size(self):
        return len(self.body)

    def __setitem__(self, name, value):
        return setattr(self, name, value)

    def __getitem__(self, name):
        return getattr(self, name)

def parse_content_disposition(con_dis):
    """解析multipart中的数据头部中的Content-Dispoition字段"""
    _con_dis = {}
    _key = ''
    for _field in con_dis.split('; '):
        if '=' not in _field:
            continue
        key, value = _field.split('=', 1)
        value = value[1: -1] # 去掉两边的绰号
        _con_dis[key] = value

    return _con_dis

def parse_multipart_form_data(content_type, body, args, files):
    boundary = content_type.split('boundary=')[-1]
    end_index = body.rfind(b'--' + boundary + '--')
    if end_index == -1: # 如果没有结尾符的话，则说明这个主体格式是错误的
        gen_log.error('Invalid multipart/form-data: no final boundary')
        return

    parts = body[:end_index].strip().split(b'--' + boundary + CRLF)
    for _part in parts:
        if not _part:
            continue
        _args_part, _body_part = _part.split(CRLF * 2)[:2]
        body = _body_part[:-2]
        headers = HTTPHeaders._parse_headers(_args_part) # 这里的headers是指某一个数据块的头部信息
        con_dis = headers.get('Content-Disposition', None)
        if not con_dis:
            gen_log.error('must have Content-Disposition')
            return

        con_dis = parse_content_disposition(con_dis)

        name = con_dis['name']
        if 'filename' in con_dis: # 如果有filename，则表示这是一个文件
            filename = con_dis.get('filename')
            if not filename:
                continue

            files.setdefault(name, []).append(
                    HTTPFile(filename = filename, body = body,
                            content_type = headers.get('Content-Type', 'application/octet-stream')))
        else:
            args.setdefault(name, []).append(body)

def get_request(connection, real_ip=True):
    """在刚连接时，获取用户的http请求信息, socket是客户端的socket"""
    if connection.is_close(): # 如果连接出错而被关闭，则返回 False，立刻结束本此请求
        return False
    try:
        _first_line, _headers = connection.parse_request_headers() # 把收到的信息分析出来
        headers = HTTPHeaders(_headers) # 这是http headers信息，类型是dict
        method , uri, version = map(lambda s: s.strip(), _first_line.split())
        _body = connection.read_body(int(headers.get('Content-Length', 0))) # 防止有body数据没有被读完，根据header中 的Content-Length再去读一下, 直到长度达到指定值
        http_request = HTTPRequest(method = method, uri = uri, version = version,
            headers = headers, body = _body, connection = connection, real_ip = real_ip)
        http_request._parse_body()
        return http_request

    except Exception as e:
        connection.close()
        traceback.print_exc()

