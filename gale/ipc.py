#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-09-15 08:31:23
# Filename      : ipc.py
# Description   : 
from __future__ import print_function
from gale.utils import set_close_exec
from gale.e import IPCError
from gevent import socket
import json
import gevent
import os
import tempfile

class FRAME():
    OPERA = 2 # 操作符的位数
    DATA_LENGTH = 8 # 数据的位数

class OPERA():
    pass

def genearte_sock_path():
    pid = os.pid()
    sock_path = os.path.join(tempfile.gettemppdir(), 'gale_ipc_%s' % pid)

    return sock_path

class IPCServer(object):
    def __init__(self, processes):
        if (processes <= 1):
            raise IPCError('ipc server must processes > 1') # 单进程需要共享数据干啥子
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        set_close_exec(self._socket.fileno())
        self._socket.bind(sock_path)
        self._socket.listen(processes)

    def serve_forever(self):
        while True:
            ipc_client, addr = self._socket.accept()
            print('new ipc_client', ipc_client, addr)
            connecction = IPCConnection(ipc_client)
            gevent.spawn(connecction.start_work)

class IPCConnection(object):
    def __init__(self, ipc_client):
        self.ipc_client = ipc_client

    def start_work(self):
        while True:
            header = self.on_frame_header()

    def on_frame_header(self):
        header = self.ipc_client.recv(FRAME.OPERA + FRAME.DATA_LENGTH) # 先获取ipc数据库
        opera = 

