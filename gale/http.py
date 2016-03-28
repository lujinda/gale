#!/usr/bin/env python
#coding:utf8
# Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-26 13:16:10
# Filename        : gale/http.py
# Description     : 
from gale.config import CRLF
from gale.e import HeaderFormatError, NotSupportHttpVersion, JSONError
from gale.utils import urlsplit, urldecode
from gale.log import gen_log
from gale import escape
from gale.escape import native_str
from gale import cache
from time import time
import re
import json


class HTTPRequest():
    def __init__(self, method, uri, version, headers, body, connection, real_ip = True):
        self.method = native_str(method)
        self.uri = native_str(uri)
        self.version = native_str(version)
        self.version_num = self.__version_num() 
        self.headers = headers
        self.body = body
        _urlparse = urlsplit(self.uri)
        self.path = _urlparse.path
        self.host = headers.get('Host', '').strip()
        self.host, self.port = (self.host.split(':') + ['80'])[:2]
        self.query = _urlparse.query
        self.connection = connection
        self._start_time = time()
        self.real_ip = real_ip
        self.cookies = self.__get_cookies()
        self.files = {}
        self._body_arguments = {}
        self.client_ip = self.__remote_ip()
        self.client_port = self.connection.remote_port()

    @property
    def size(self):
        """return requesty body size"""
        return len(self.body)

    @property
    def first_line(self):
        return "{method} {uri} {version}".format(
                method = self.method, uri = self.uri, version = self.version)

    def _parse_body(self):
        content_type = self.headers.get(u'Content-Type', '')

        try:
            if content_type.startswith('multipart/form-data'):
                parse_multipart_form_data(content_type, self.body, args = self._body_arguments,
                        files = self.files)
            else:
                self._body_arguments = urldecode(self.body) 
        except Exception:
            self._body_arguments = {}

    @cache.cache_self
    def json(self):
        try:
            json_body = json.loads(self.body)
        except ValueError:
            raise JSONError

        return json_body

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

    def __remote_ip(self):
        if self.real_ip: 
            _remote_ip = self.headers.get("X-Real-IP", 
                self.headers.get("X-Forwarded-For", self.connection.remote_ip()))
        else:
            _remote_ip = self.connection.remote_ip()

        return _remote_ip

    @property
    def start_time(self):
        return self._start_time

    @property
    def request_time(self):
        return time() - self._start_time

    def get_header(self, name, default = None):
        """获取http header，不区分大小写, 并且Referrer和Referer都是一样的"""
        name = name.title()
        if name == 'Referrer':
            name = 'Referer'

        return self.headers.get(name, default)

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
    def __init__(self, headers=None, is_request = False):
        dict.__init__(self)
        self.__is_request = is_request
        headers = headers or {}
        self._headers_map_list = {} # 数据格式: {name: [value1, value2,...]}

        if not isinstance(headers, dict): # 如果传入的headers不是字典，表示这是请求headers，则调用dict原有的__setitem__ 将头信息传进去，如果传入是dict，则表示是响应头，则需要处理一下，比如同域名的，但是不同域值要放一块
            self.__is_request = True
            headers = self._parse_headers(headers)
            for _k, _v in headers.items():
                dict.__setitem__(self, _k.title(), _v)

        for _k, _v in headers.items():
            self[_k] = _v

    @staticmethod
    def _parse_headers(headers):
        """把http头信息组织到一个字典中去"""
        _headers = {}
        _last_key = None
        headers = native_str(headers)
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
        _headers_string = escape.utf8(first_line)
        for _name, _value_list in self._headers_map_list.items():
            for _value in _value_list:
                _header_line = "{name}: {value}".format(
                    name = _name, value = _value)
                _headers_string += (CRLF + escape.utf8(_header_line))

        return _headers_string + CRLF * 2


    def get_headers_items(self):
        items = []
        for key, values in self._headers_map_list.items():
            for value in values:
                items.append((key, value))
        return items

    def __setitem__(self, name, value):
        self._headers_map_list[name] = [value]

    def clear(self):
        self._headers_map_list.clear()

    def __getitem__(self, name):
        if name in self._headers_map_list:
            return self._headers_map_list[name][0]
        else:
            raise KeyError

    def set_default_header(self, name, value):
        if name not in self._headers_map_list:
            self[name] = value

    def get(self, name, default = None):
        if self.__is_request:
            return dict.get(self, name, default)
        if name not in self._headers_map_list:
            return default

        return self.__getitem__(name)

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
    for _field in con_dis.split(b'; '):
        if b'=' not in _field:
            continue
        key, value = _field.split(b'=', 1)
        value = value[1: -1] # 去掉两边的绰号
        _con_dis[key] = value

    return _con_dis

def parse_multipart_form_data(content_type, body, args, files):
    boundary = escape.utf8(content_type.split('boundary=')[-1])
    end_index = body.rfind(b'--' + boundary + b'--')
    if end_index == -1: # 如果没有结尾符的话，则说明这个主体格式是错误的
        gen_log.error('Invalid multipart/form-data: no final boundary')
        return

    parts = body[:end_index].split(b'--' + boundary + CRLF)
    for _part in parts:
        if not _part:
            continue
        _args_part, _body_part = _part.split(CRLF * 2)[:2]
        body = _body_part[:-2]
        headers = HTTPHeaders._parse_headers(_args_part) # 这里的headers是指某一个数据块的头部信息
        con_dis = headers.get(b'Content-Disposition', None)
        if not con_dis:
            gen_log.error('must have Content-Disposition')
            return

        con_dis = parse_content_disposition(con_dis)

        name = escape.to_unicode(con_dis[b'name'])
        if b'filename' in con_dis: # 如果有filename，则表示这是一个文件
            filename = con_dis.get(b'filename')
            if not filename:
                continue

            files.setdefault(name, []).append(
                    HTTPFile(filename = escape.to_unicode(filename), body = body,
                            content_type = escape.to_unicode(headers.get(b'Content-Type', 'application/octet-stream'))))
        else:
            args.setdefault(name, []).append(escape.to_unicode(body))

