#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-11 15:37:12
# Filename      : wsgi.py
# Description   : 
from __future__ import print_function
from .http import HTTPRequest
from gale.escape import native_str
from gale.web import Application

class WSGIApplication(Application):
    def __call__(self, env, start_response, app_instance = None):
        app_instance = app_instance or self
        http_request = HTTPRequest(env)
        http_request._parse_body()
        from gale import web
        handler = Application.__call__(app_instance, http_request, is_wsgi = True)

        if hasattr(handler, '_new_cookie'):
            for cookie in handler._new_cookie.values():
                handler.add_header('Set-Cookie', cookie.OutputString())


        status = "%s %s" % (handler._status_code, handler._status_mess)


        _body = b''.join(handler._push_buffer)

        if http_request.method == 'HEAD': # 如果是HEAD请求的话则不返回主体内容
            _body = b''

        if handler._status_code != 304: 
            handler.set_header('Content-Length', len(_body))

        headers = [(native_str(_k), str(native_str(_v))) for _k, _v in handler._headers.get_headers_items()] # 在python2.7 中，不允许headers是unicode
        write = start_response(native_str(status), headers) 

        write(_body)
        handler.log_print()
        handler.on_finish()
        return []

