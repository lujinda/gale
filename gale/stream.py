#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-04-19 12:57:50
# Filename      : stream.py
# Description   : 
from __future__ import print_function
import gevent
from gale.httpconnection import HTTPConnection 
from gale.autoreload import check_files
from gale import utils
import sys
import time
import os
from gevent import sleep
import signal

def monitor_files():
    while True:
        check_files()
        sleep(0.2)

class StreamServer(object):
    def __init__(self, listen_add, callback, settings, reuse_add = True, autoreload = False):
        self._socket = utils.get_gale_socket()


        self._socket.bind(listen_add)
        self._socket.listen(settings.max_client)
        self._callback = callback
        self.timeout = settings.timeout
        self.autoreload = autoreload

        self.settings = settings

    def __autoreload(self):
        gevent.spawn(monitor_files)

    def serve_forever(self, in_sub = False):
        if in_sub: # 只在子进程中才忽略掉中断信号
            signal.signal(signal.SIGINT, signal.SIG_IGN)

        if self.autoreload:
            self.__autoreload()

        while True:
            s, addr = self._socket.accept()
            s = utils.get_gale_socket(s)
            try:
                s.settimeout(self.timeout) # 设置客户端的超时时间
                connection = HTTPConnection(s)
                gevent.spawn(connection.get_request, self._callback,
                                server_settings = self.settings).link_exception(connection.gevent_exception) # 当成功生成一个request时，就会把request传入callback中去，一般是Application
            except Exception as e:
                s.close()

    def raise_error(self, g):
        g.kill()

