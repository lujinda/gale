#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-12 12:44:18
# Filename      : http.py
# Description   : 
from __future__ import unicode_literals
from gale.http import HTTPRequest as _HTTPRequest, HTTPHeaders
from time import time

class HTTPRequest(_HTTPRequest):
    def __init__(self, env):
        self.method = env['REQUEST_METHOD']
        self.uri = self.path = env['PATH_INFO']
        self.query = env.get('QUERY_STRING')
        if self.query:
            self.uri += '?' + self.query
        self.version = 'HTTP/1.1'
        self.version_num = self.__version_num()
        if env.get('HTTP_HOST'):
            self.host = env['HTTP_HOST']
        else:
            self.host = env['SERVER_NAME']

        self.host = self.host.split(':')[0]

        self.port = env.get('SERVER_PORT', 80)

        headers = HTTPHeaders(is_request = True)
        if env.get('CONTENT_TYPE'):
            dict.__setitem__(headers, 'Content-Type', env['CONTENT_TYPE'])

        if env.get('CONTENT_LENGTH'):
            content_length = env.get('CONTENT_LENGTH')
            dict.__setitem__(headers, 'Content-Length', content_length)
            self.body = env['wsgi.input'].read(int(content_length))
        else:
            self.body = ''

        self.remote_addr = env['REMOTE_ADDR']
        self._start_time = time()

        for key in env:
            if key.startswith("HTTP_"):
                dict.__setitem__(headers, key[5:].title().replace('_', '-'), env[key])

        self.headers = headers
        self.cookies = self.__get_cookies()
        self.files = {}
        self._body_arguments = {}

    @property
    def client_ip(self):
        return self.remote_addr


