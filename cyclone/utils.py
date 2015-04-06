#!/usr/bin/env python
#coding:utf8
# Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-26 13:14:11
# Filename        : cyclone/utils.py
# Description     : 
import sys
from urlparse import urlsplit
import email.utils
import time

is_py3 = sys.version[0] == '3'

def urldecode(params_url):
    if not params_url: # 如果没有东西的话，就返回{}
        return {}

    _d = {} # 存的是请求参数的字典形式，值是参数值列表
    for _name, _value in map(lambda x: x.split('=', 1), 
            filter(lambda k_v: '=' in k_v, params_url.split('&'))): # filter 是为了把不带有=号的参数去掉
        _d.setdefault(_name, []).append(_value)

    return _d

code_mess_map = {
            100: 'Continue',
            101: 'Switching Protocols',
            200: 'OK',
            201: 'Created',
            202: 'Accepted',
            203: 'Non-Authoritative Information',
            204: 'No Content',
            205: 'Reset Content',
            206: 'Partial Content',
            300: 'Multiple Choices',
            301: 'Moved Permanently',
            302: 'Found',
            303: 'See Other',
            304: 'Not Modified',
            305: 'Use Proxy',
            307: 'Temporary Redirect',
            400: 'Bad Request',
            401: 'Unauthorized',
            402: 'Payment Required',
            403: 'Forbidden',
            404: 'Not Found',
            405: 'Method Not Allowed',
            406: 'Not Acceptable',
            407: 'Proxy Authentication Required',
            408: 'Request Timeout',
            409: 'Conflict',
            410: 'Gone',
            411: 'Length Required',
            412: 'Precondition Failed',
            413: 'Request Entity Too Large',
            414: 'Request-URI Too Long',
            415: 'Unsupported Media Type',
            416: 'Requested Range Not Satisfiable',
            417: 'Expectation Failed',
            500: 'Internal Server Error',
            501: 'Not Implemented',
            502: 'Bad Gateway',
            503: 'Service Unavailable',
            504: 'Gateway Timeout',
            505: 'HTTP Version Not Supported'
            }

def format_timestamp(ts = None):
    if not ts:
        ts = time.time()
    return email.utils.formatdate(ts, usegmt = True)

