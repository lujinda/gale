#/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-04-19 12:57:50
# Filename      : stream.py
# Description   : 
from __future__ import print_function
from gevent import socket
import gevent
from gale.http import HTTPConnection 
import sys

class StreamServer(object):
    def __init__(self, listen_add, callback, max_client = 1000, reuse_add = True, timeout = 15):
        self._socket = socket.socket(socket.AF_INET, 
                socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, 
                socket.SO_REUSEADDR, reuse_add)
        self._socket.bind(listen_add)
        self._socket.listen(max_client)
        self._callback = callback
        self.timeout = timeout

    def serve_forever(self):
        while True:
            try:
                s, addr = self._socket.accept()
                s.setsockopt(socket.SOL_SOCKET, 
                    socket.SO_REUSEADDR, 1)
                s.settimeout(self.timeout) # 设置客户端的超时时间
                connection = HTTPConnection(s)
                gevent.spawn(connection.get_request, self._callback).link_exception(connection.gevent_exception)
            except Exception as e:
                s.close()

    def raise_error(self, g):
        g.kill()

