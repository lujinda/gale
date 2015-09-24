#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-09-15 08:31:23
# Filename      : ipc.py
# Description   : 
from __future__ import print_function
from gale.utils import set_close_exec, ObjectDict, single_pattern
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
import signal

__all__ = ['IPCServer','IPCDict']

ALL_OPERA = {'set': False, 'get': True, 'items': True, 'has_key': True,
        'pop': True, 'popitem': True, 'update': False, 'values': True,
        'setdefault': True, 'keys': True, 'clear': False, 'del': False, 
        'incr': True}

class FRAME():
    DATA_LENGTH = 8 # 数据的位数

def genearte_sock_path(is_sub = False):
    return '/tmp/gale.sock'

class _Memory(dict):
    def _set(self, name, value):
        self[name] = value

    def _del(self, name):
        try:
            del self[name]
        except KeyError:
            pass

    def _incr(self, name, increment = 1):
        if not isinstance(increment, int):
            raise TypeError('increment type must be int')
        current = self.setdefault(name, 0)
        self[name] = current + increment

        return self[name]

@single_pattern
class IPCMemory(object):
    _memory_block = {}

    def __getitem__(self, name):
        return self._memory_block.setdefault(name, _Memory())

@single_pattern
class IPCServer(object):
    def __init__(self):
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        set_close_exec(self._socket.fileno())
        sock_path = genearte_sock_path()
        try:
            os.remove(sock_path)
        except OSError as e:
            if e.errno != 2: # 2表示no such file or direrctory
                raise e
            
        self._socket.bind(genearte_sock_path())
        self._socket.listen(50)

    def serve_forever(self):
        Process(target = self._serve_forever).start()

    def _serve_forever(self):
        signal.signal(signal.SIGINT, self.close)
        while not self._socket.closed:
            try:
                conn, addr = self._socket.accept()
            except socket.error:
                self.close()
                break
            connection = IPCConnection(conn)
            gevent.spawn(connection.start_work)

    def close(self, *args):
        if self._socket.closed:
            return

        os.remove(self._socket.getsockname())
        self._socket.close()

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
        self._socket.close()

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
        frame += struct.pack(b'!Q', data_length)
        frame += data
        self._socket.sendall(frame)

class IPCConnection(Connection):
    def start_work(self):
        while True:
            frame = self.recv_parse_frame()
            if not frame:
                break
            self.exec_ipc(json.loads(frame.data))


    def exec_ipc(self, data):
        ipc_memory = IPCMemory()
        name, command, args, kwargs = data
        need_return = ALL_OPERA[command]

        if command not in dir({}):
            command = '_' + command

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


    def __delitem__(self, name):
        return self._exec_ipc('del', name)

