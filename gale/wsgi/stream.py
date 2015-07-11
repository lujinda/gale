#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-12 12:29:59
# Filename      : stream.py
# Description   : 
from wsgiref import simple_server
from gale.autoreload import check_files
from functools import partial
from threading import Thread
from time import sleep
from gale.utils import set_close_exec

def wsgi_callback(cls, env, start_response):
    from .web import WSGIApplication
    wsgi_app = WSGIApplication()
    return wsgi_app(env, start_response, cls)

def monitor_files():
    while True:
        check_files()
        sleep(1)

class StreamServer(object):
    """为了兼容py3，py3的server用得是wsgi server"""
    def __init__(self, listen_add, callback, max_client = 1000, reuse_add = True, timeout = 15, autoreload = False):
        host, port = listen_add
        _server = simple_server.make_server(host, port, partial(wsgi_callback, callback))
        _server.timeout = timeout
        _server.request_queue_size = max_client
        _server.allow_reuse_address = reuse_add
        set_close_exec(_server.fileno())

        self._server = _server
        self.autoreload = autoreload

    def __autoreload(self):
        t = Thread(target = monitor_files)
        t.setDaemon(True)
        t.start()

    def serve_forever(self):
        if self.autoreload:
            self.__autoreload()
        self._server.serve_forever()

