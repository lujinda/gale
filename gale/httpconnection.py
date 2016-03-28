#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-12 09:46:47
# Filename      : httpconnection.py
# Description   : 
from gale.config import CRLF
import traceback
from gale.http import HTTPHeaders, HTTPRequest
from gale.iosocket import IOSocket
from gevent import socket

class HTTPConnection(IOSocket):
    def parse_request_headers(self):
        """从原始数据中提取头信息"""
        _first_line, _headers = (self._headers.split(CRLF, 1) +  [''])[:2]
        self._headers = ''
        return _first_line, _headers

    def read_body(self, max_length):
        if max_length == 0: # 如果请求headers中没有指定 Content-Type或者为0,表示没有请求主体
            return b''

        body = self._buff # _buff里的内容是在读取 headers时多读取的数据
        while len(body) < max_length:
            _body_data = self._socket.recv(self.max_buff)
            if not _body_data:
                break
            body += _body_data

        self._buff = b''
        return body

    def read_headers(self):
        eof = -1
        _headers = b''
        while True:
            try:
                _data = self._socket.recv(self.max_buff)
            except socket.error:
                _data = None
            if not _data:
                break
            self._buff += _data
            eof = self._buff.find(CRLF * 2)
            if eof != -1:
                _headers, self._buff = self._buff[:eof], self._buff[eof + len(CRLF * 2):]
                break

        return _headers.strip()

    def get_request(self, callback, **kwargs):
        """获取用户的请求信息，并可以成功取得一个http请求时，生成一个HTTPRequest, 并激活回调函数(application的__call__)"""
        while True and self.closed == False:
            try:
                _headers = self.read_headers()
            except socket.timeout: # socket超时的异常不报
                _headers = None

            if not _headers:
                self.close()
                break

            self._headers = _headers
            request = get_request(self)
            kwargs['is_wsgi'] = False
            callback(request, **kwargs)

    def send_headers(self, headers_string):
        """headers_string是已经被处理过了的头信息，直接写入就行"""
        self.send_string(headers_string)

    def send_body(self, body_string):
        """同send_headers"""
        self.send_string(body_string)

    def send_finish_tag(self):
        self.send_string(CRLF)

    def remote_ip(self):
        return self._socket.getpeername()[0]

    def remote_port(self):
        return self._socket.getpeername()[1]

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

