#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-09-15 08:31:23
# Filename      : ipc.py
# Description   : 
from __future__ import print_function
from gale.utils import set_close_exec, ObjectDict
from gale.e import IPCError
from gevent import socket
import gevent
import json
from multiprocessing import Process
import os
import tempfile
import time
import struct
from functools import partial

__all__ = ['IPCServer','IPCDict']

ALL_OPERA = {'set': False, 'get': True, 'items': True, 'has_key': True,
        'pop': True, 'popitem': True, 'update': False, 'values': True,
        'setdefault': True, 'keys': True, 'clear': False}

class FRAME():
    DATA_LENGTH = 8 # 数据的位数

def genearte_sock_path(is_sub = False):
    return '/tmp/gale.sock'

class _Memory(dict):
    def set(self, name, value):
        self[name] = value

class IPCMemory(object):
    _memory_block = {}
    def __new__(cls, *args, **kwargs):
        if hasattr(IPCMemory, '_instance'):
            return IPCMemory._instance
        _instance = object.__new__(cls, *args, **kwargs)
        IPCMemory._instance = _instance
        return _instance

    def __getitem__(self, name):
        return self._memory_block.setdefault(name, _Memory())

class IPCServer(object):
    is_start = False
    def __new__(cls, *args, **kwargs):
        if hasattr(IPCServer, '_instance'):
            return IPCServer._instance
        _instance = object.__new__(cls, *args, **kwargs)
        IPCServer._instance = _instance
        return _instance

    def __init__(self):
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        set_close_exec(self._socket.fileno())
        sock_path = genearte_sock_path()
        try:
            os.remove(sock_path)
        except OSError:
            pass

        self._socket.bind(genearte_sock_path())
        self._socket.listen(50)

    def serve_forever(self):
        p = Process(target = self._serve_forever)
        p.start()

    def _serve_forever(self):
        if self.is_start:
            return

        self.is_start = True
        while True:
            conn, addr = self._socket.accept()
            connection = IPCConnection(conn)
            gevent.spawn(connection.start_work)

class Connection(object):
    def __init__(self, _socket):
        self._socket = _socket

    def recv_parse_frame(self):
        frame = ObjectDict()
        self.on_frame_header(frame)
        if not frame:
            self.close()
            return 

        self.on_frame_data(frame)

        return frame

    def close(self):
        self.conn.close()

    def on_frame_header(self, frame):
        _header = ObjectDict()
        header = self._socket.recv(FRAME.DATA_LENGTH) # 先获取ipc数据库
        if not header:
            return

        data_length = struct.unpack(b'!Q', header)[0]
        _header.data_length = data_length

        frame.update(_header)

    def on_frame_data(self, frame):
        data_length = frame.data_length
        data = self._recv_data(data_length)
        frame.data = data

    def _recv_data(self, data_length):
        assert data_length > 0
        chunk = []
        while True:
            _data = self._socket.recv(data_length)
            _len = len(_data)
            assert _len <= data_length

            chunk.append(_data)
            if len(_data) == data_length:
                break
            data_length -= _len

        return b''.join(chunk)

    def _send_data(self, data):
        """这里的data是已经处理好了的"""
        frame = b''
        data_length = len(data)
        frame += struct.pack('!Q', data_length)
        frame += data
        self._socket.sendall(frame)

class IPCConnection(Connection):
    def start_work(self):
        while True:
            frame = self.recv_parse_frame()
            self.exec_ipc(json.loads(frame.data))


    def exec_ipc(self, data):
        ipc_memory = IPCMemory()
        name, command, args, kwargs = data
        need_return = ALL_OPERA[command]
        exec_func = getattr(ipc_memory[name], command)
        result = exec_func(*args, **kwargs)

        if not need_return: # 如果不需要返回值，则就此结束了
            return
        self._send_data(json.dumps(result))

class IPCClient(Connection):
    def __init__(self, name):
        _socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock_path = genearte_sock_path(True)
        _socket.connect(sock_path)
        self.name = name
        Connection.__init__(self, _socket)

    def _exec_ipc(self, command, *args, **kwargs):
        need_return =  ALL_OPERA[command]
        frame_data = self.generate_frame_data(command, *args, **kwargs)
        self._send_data(frame_data)
        if not need_return:
            return

        return self.__get_ipc_return()

    def __get_ipc_return(self):
        frame = self.recv_parse_frame()
        if not frame:
            return
        
        data = frame.data
        return json.loads(data)

    def generate_frame_data(self, command, *args, **kwargs):
        return json.dumps([self.name, command, args, kwargs])

class IPCDict(IPCClient): 
    def __getattr__(self, name):
        if name.startswith('_'):
            return self.__dict__[name]

        if name not in ALL_OPERA:
            name = 'get'

        return partial(self._exec_ipc, name)

    def __getitem__(self, name):
        return self.get(name)

    def __setitem__(self, name, value):
        self.set(name, value)

