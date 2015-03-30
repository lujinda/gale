#!/usr/bin/env python
#coding:utf8
# Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-26 13:14:37
# Filename        : cyclone/server.py
# Description     : 
from __future__ import unicode_literals, print_function

import gevent
from cyclone.socket import StreamServer

class HTTPServer(object):
    """
        http server
    """
    listen_add = (None, None)

    def __init__(self, callback, listen_add = (None, None), stop_timeout = 1, max_client = 1000):
        assert callable(callback) # callback必须是可调用的
        self._callback = callback # 表示回调函数
        self.stop_timeout = stop_timeout
        self.listen(listen_add)
        self.max_client = max_client 

    def listen(self, listen_add):
        self.listen_add = listen_add

    def run(self, listen_add = None):
        if isinstance(listen_add, (tuple, list)):
            self.listen(listen_add)
        _server = StreamServer(self.listen_add, self._callback, 
                max_client = self.max_client)
        #_server.stop_timeout = self.stop_timeout
        _server.serve_forever()

    @property
    def port(self):
        return self.listen_add[1]

    @property
    def host(self):
        return self.listen_add[0]

