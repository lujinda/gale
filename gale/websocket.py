#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-09-08 14:04:23
# Filename      : websocket.py
# Description   : 
from __future__ import unicode_literals, print_function
import base64
import struct
import hashlib
from gale.escape import utf8
from gale.utils import urlsplit, ObjectDict, is_string
from gale.web import RequestHandler, async, HTTPError
from gale.e import WebSocketError

WS = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'

def generate_response_key(websocket_key):
    return base64.encodestring(hashlib.sha1(websocket_key + WS).digest()).strip()


class WebSocketConnection(object):
    def __init__(self, websocket_version, websocket_key, handler):
        self.websocket_version = websocket_version
        self.websocket_key = websocket_key
        self.handler = handler
        self.stream = handler.request.connection
        self.stream.set_timeout(100)
        self.closed = False
        self.close_status = None
        self.close_reason = None

    def accept(self):
        response = [
                'HTTP/1.1 101 Switching Protocols',
                'Upgrade: websocket',
                'Connection: Upgrade',
                'Sec-WebSocket-Accept: %s' % (generate_response_key(self.websocket_key)),
                ]
        response = utf8('\r\n'.join(response) + '\r\n' * 2)
        self.stream.write(response)
        self.handler.on_open()
        while self.closed == False:
            frame_data = self.recv_frame_data()
            if frame_data.opcode == 0x1: # 接受text
                self.handler.on_message(frame_data)
            elif frame_data.opcode == 0x8: # 关闭
                _data = frame_data.data
                if len(_data) >= 2:
                    self.close_status = struct.unpack(b'!H', _data[:2])[0]
                if len(_data) > 2:
                    self.close_reason = _data[2:]
                self.close()

            elif frame_data.opcode == 0x9: # on ping
                self.handler.on_ping(frame_data)

    def close(self):
        if self.closed:
            return
        self.stream.close()
        self.handler.on_close(self.close_status, self.close_reason)
        self.closed = True

    def recv_frame_data(self):
        frame = ObjectDict()
        _header_data = self.recv_bytes(2)
        if not _header_data:
            return None
        self._on_frame_header(_header_data, frame)


        if frame.payload_len < 126:
            pass
        elif frame.payload_len == 126:
            frame.payload_len = struct.unpack(b'!H', self.recv_bytes(2))[0]
            # frame.payload_len = sum([ _d & (0xFF << (base * 8)) for base in range(2)])
        elif frame.payload_len == 127:
            frame.payload_len  = struct.unpack(b'!Q', self.recv_bytes(8))[0]
            # frame.payload_len = sum([ _d & (0xFF << (base * 8)) for base in range(4)])

        if frame.mask:
            self._on_frame_mask_key(self.recv_bytes(4), frame)
    
        self._on_frame_data(self.recv_bytes(frame.payload_len), frame)

        return frame

    def send_frame_data(self, frame):
        bin_frame = b''
        bin_frame += struct.pack(b'B', (frame.fin << 7)  + frame.opcode)
        payload_len = len(frame.data)

        if payload_len < 126:
            bin_frame += struct.pack(b'B', payload_len)

        elif payload_len <= 0xffff:
            bin_frame += struct.pack(b'B', 126)
            bin_frame += struct.pack(b'!H', payload_len)

        else:
            bin_frame += struct.pack(b'B', 127)
            bin_frame += struct.pack(b'!Q', payload_len)

        bin_frame += frame.data

        self.stream.send_string(bin_frame)

    def recv_bytes(self, size):
        if size == 0:
            return b''

        chunk = self.stream.recv(size)

        if not chunk:
            raise WebSocketError('connection closed')

        has_much = size - len(chunk) # 因为一次只能获取65536长度的数据，所以需要检测下有没有余下的
        if has_much > 0:
            chunk += self.recv_bytes(has_much)

        if len(chunk) != size:
            raise WebSocketError('connection closed')
        
        return chunk

    def _on_frame_data(self, _buffer, frame):
        if not frame.mask:
            frame['data'] = _buffer
            return

        _content = b''
        for i in range(frame.payload_len):
            _b = struct.unpack(b'!B', _buffer[i])[0]
            _content += struct.pack(b'!B', _b ^ frame.mask_key[i % 4])

        frame['data'] = _content

    def _on_frame_mask_key(self, _buffer, frame):
        frame['mask_key'] = struct.unpack(b'4B', _buffer)

    def _on_frame_header(self, _buffer, frame):
        _d = struct.unpack(b'BB', _buffer)
        frame['fin'] = _d[0] >> 7
        frame['opcode'] = _d[0] & 0xF
        frame['mask'] = _d[1] >> 7
        frame['payload_len'] = _d[1] & 0x7F

class WebSocketHandler(RequestHandler):
    @async
    def GET(self):
        request_error = self.check_request_header_error()
        if request_error:
            self.set_status(400)
            self.finish(request_error)
            return

        if not self.origin_is_accept():
            self.set_status(403)
            self.finish('access origin illegal')
            return

        self._websocket_conn = WebSocketConnection(self.__websocket_version,
                self.__websocket_key, self)
        try:
            self._websocket_conn.accept()
        except WebSocketError as ex:
            self._websocket_conn.close()

    def close(self):
        self._websocket_conn.close()

    def on_open(self):
        pass

    def on_close(self, status, reason):
        pass

    def on_message(self, frame):
        pass

    def on_ping(self, frame):
        pass

    def send_message(self, chunk):
        if not is_string(chunk):
            raise WebSocketError('message type must str or unicode')
        frame = ObjectDict({'fin': 1, 'data': utf8(chunk), 'opcode': 1})
        self._websocket_conn.send_frame_data(frame)

    def check_request_header_error(self):
        for header in ('upgrade', 'websocket_key', 'websocket_version'):
            _error = getattr(self, '_check_'  + header)()
            if _error:
                return _error

        return None

    @property
    def __websocket_key(self):
        return self.request.get_header('Sec-WebSocket-Key', '')

    @property
    def __websocket_version(self):
        _version = self.request.get_header('Sec-WebSocket-Version')
        return _version and int(_version) or None

    def _check_upgrade(self):
        upgrade = self.request.get_header('Upgrade', '')
        if upgrade.lower() != 'websocket':
            return 'upgrade only support websocket'

    def _check_websocket_version(self):
        _version = self.__websocket_version
        if (not _version) or (_version != 13):
            self.set_header('Sec-WebSocket-Version', '13')
            return 'currently support version == 13'

    def _check_websocket_key(self):
        if not self.__websocket_key:
            return 'missing websocket key'

    def origin_is_accept(self):
        origin = utf8(self.request.get_header('Origin', ''))
        if not origin:
            return False

        origin_host = urlsplit(origin).netloc
        origin_host = ':' in origin_host and origin_host or (origin_host + ':80')
        if origin_host != self.request.host + ':' + self.request.port:
            return False

        return True

