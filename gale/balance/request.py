#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-11-27 15:01:54
# Filename      : request.py
# Description   : 
from __future__ import print_function, unicode_literals

import socket
try:
    import httplib # py2
except ImportError:
    from http import client as httplib
import gale
import gevent
import gevent.monkey

__all__ = ['proxy_request']
gevent.monkey.patch_socket()

def proxy_request(request, upstream):
    host, port = (upstream.split(':', 1) + [80])[:2]
    _conn = httplib.HTTPConnection(host = host,
            port = int(port))
    request.headers['X-Forwarded-For'] = request.real_ip
    request.headers['X-Real-IP'] = request.real_ip
    request.headers['Host'] = upstream
    request.headers['Connection'] = 'close'
    try:
        _conn.request(request.method, request.uri, body = request.body,
            headers = request.headers)
    except socket.error:
        raise gale.e.WorkerOffline
    response = _conn.getresponse()

    return response

