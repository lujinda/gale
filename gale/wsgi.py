#/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-11 15:37:12
# Filename      : wsgi.py
# Description   : 
from __future__ import print_function
from gale.web import Application
from gale.http import HTTPRequest, HTTPHeaders
from gale.escape import native_str
from time import time

class WSGIApplication(Application):
    def __init__(self, *args, **kwargs):
        super(WSGIApplication, self).__init__(*args, 
                **kwargs)

    def __call__(self, env, start_response):
        http_request = HTTPRequest(env)
        http_request._parse_body()
        handler = Application.__call__(self, http_request, is_wsgi = True)

        if hasattr(handler, '_new_cookie'):
            for cookie in handler._new_cookie.values():
                handler.add_header('Set-Cookie', cookie.OutputString())


        status = "%s %s" % (handler._status_code, handler._status_mess)


        _body = b''.join(handler._push_buffer)

        if http_request.method == 'HEAD': # 如果是HEAD请求的话则不返回主体内容
            _body = b''

        if handler._status_code != 304: 
            handler.set_header('Content-Length', len(_body))

        headers = [(native_str(_k), native_str(_v)) for _k, _v in handler._headers.get_headers_items()] # 在python2.7 中，不允许headers是unicode
        write = start_response(native_str(status), 
            headers, exc_info = False)

        write(_body)
        handler.log_print()
        handler.on_finish()
        return []

class HTTPRequest(HTTPRequest):
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

        headers = HTTPHeaders()
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

