#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-12-11 16:54:04
# Filename      : stream.py
# Description   : 
from __future__ import print_function, unicode_literals
from gale import utils
import struct
import msgpack

class MonitorStream(object):
    def __init__(self, _socket):
        self._socket = utils.get_gale_socket(_socket)

    def recv_request(self):
        while True:
            request_data = self._recv_request()
            if not request_data:
                self.close()
                raise StopIteration
            else:
                yield request_data

    def _recv_request(self):
        header_buffer = self._socket.recv(2)
        data_length = struct.unpack(b'H', header_buffer)[0] # 数据包的前两个字节表示整个包的长度

        data_buffer = b''
        while True:
            data_buffer += self.worker.recv(data_length)
            if not data_buffer:
                return

            if len(data_buffer) >= data_length:
                data_buffer[]
                break
            else:
                continue

        try:
            request_data = msgpack.unpackb(data)
            assert 'params' in request_data and 'command' in request_data,\
                    'params and command must be included in the request data'
            return request_data
        except msgpack.ExtraData:
            self.close()

    def send_request(self, request):
        data_buffer = msgpack.packb(request)
        header_buffer = struct.pack(b'H', len(data_buffer))
        self._socket.sendall(header_buffer + data_buffer)

    def close(self):
        self.worker.close()

