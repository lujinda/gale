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
        self.closed = False
        gevent.spawn(self.__all_recv).join() # 从用户那接受到的所有数据，还没经过处理的

    def __all_recv(self):
        _data = self._socket.recv(self._buff)
        if not _data:
            self.close()
        self._request_data = _data

    def close(self):
        self._socket.shutdown(socket.SHUT_RDWR)
        self._socket.close()
        self.closed = True

    def send_string(self, string):
        self._socket.send(string)

    def is_close(self):
        if self.closed:
            return True
        try:
            if (self._socket.getpeername()): # 如果 closed是False,为了避免有时socket会异常断开，就再判断一下
                return False
        except:
            return True

class StreamServer(object):
    def __init__(self, listen_add, callback, max_client = 1000, reuse_add = True, timeout = 60):
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
                gevent.spawn(self._callback, s, addr).link_exception(self.raise_error)
            except Exception as e:
                s.close()

    def raise_error(self, g):
        g.kill()
