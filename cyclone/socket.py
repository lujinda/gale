#!/usr/bin/env python
#coding:utf8
# Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-26 12:55:47
# Filename        : cyclone/socket.py
# Description     : 
from __future__ import unicode_literals
from cyclone.escape import param_encode
import gevent
from gevent import socket

class IOSocket():
    def __init__(self, socket, max_buff= 4096):
        self._socket = socket
        self._buff = max_buff
        gevent.spawn(self.__all_recv).join() # 从用户那接受到的所有数据，还没经过处理的

    def __all_recv(self):
        _data = self._socket.recv(self._buff)
        self._request_data = _data

    def close(self):
        self._socket.close()

    def send_string(self, string):
        self._socket.send(string)

class StreamServer(object):
    def __init__(self, listen_add, callback, max_client = 1000, reuse_add = True):
        self._socket = socket.socket(socket.AF_INET, 
                socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, 
                socket.SO_REUSEADDR, 1)
        self._socket.bind(listen_add)
        self._socket.listen(max_client)
        self._callback = callback

    def serve_forever(self):
        while True:
            try:
                socket, addr = self._socket.accept()
                gevent.spawn(self._callback, socket, addr).link_exception(self.raise_error)
            except Exception as e:
                socket.close()

    def raise_error(self, g):
        g.kill()

