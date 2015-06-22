#!/usr/bin/env python
#coding:utf8
# Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-26 12:55:47
# Filename        : gale/socket.py
# Description     : 
from __future__ import unicode_literals
import gevent
from gevent import socket

class IOSocket():
    def __init__(self, socket, max_buff= 4096):
        self._socket = socket
        self.max_buff = max_buff
        self.closed = False
        self._buff = b''

    def gevent_exception(self, *args, **kwargs):
        self.close()

    def close(self):
        if self.closed:
            return
        self._socket.close()
        self.closed = True

    def send_string(self, string):
        try:
            self._socket.sendall(string)
        except Exception as e:
            self.closed = True

    def is_close(self):
        if self.closed:
            return True
        try:
            if (self._socket.getpeername()): # 如果 closed是False,为了避免有时socket会异常断开，就再判断一下
                return False
        except:
            return True

