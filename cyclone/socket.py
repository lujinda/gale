#!/usr/bin/env python
#coding:utf8
# Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-26 12:55:47
# Filename        : cyclone/socket.py
# Description     : 
from __future__ import unicode_literals
import gevent
from gevent import socket
from cyclone.config import CRLF

class IOSocket():
    def __init__(self, socket, max_buff= 4096):
        self._socket = socket
        self._buff = max_buff
        self.closed = False
        self._request_data = ''


    def gevent_exception(self, *args, **kwargs):
        self.close()

    def close(self):
        if self.closed:
            return
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

