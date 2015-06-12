
#coding:utf8
# Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-26 13:14:11
# Filename        : gale/utils.py
# Description     : 
from __future__ import unicode_literals
try: # py2
    from urlparse import urlsplit 
    from urllib import unquote_plus
    from urllib import quote_plus
except ImportError: # py3
    from urllib.parse import urlsplit # py3
    from urllib.parse import unquote_plus
    from urllib.parse import quote_plus

import email.utils
import time
import urllib
from gale import escape
from gale.config import CRLF
import mimetypes
import uuid

def urldecode(params_url):
    if not params_url: # 如果没有东西的话，就返回{}
        return {}

    params_url = escape.param_decode(params_url)

    _d = {} # 存的是请求参数的字典形式，值是参数值列表
    for _name, _value in map(lambda x: x.split('=', 1), 
            filter(lambda k_v: '=' in k_v, params_url.split('&'))): # filter 是为了把不带有=号的参数去掉
        # 对用户提交的url参数和body进行解码成unicode

        _d.setdefault(_name, []).append(urlunquote(_value))
    return _d

def urlunquote(param):
    param = unquote_plus(escape.native_str(param))
    return escape.param_decode(param)

def urlquote(param):
    return quote_plus(escape.utf8(param))

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


def get_mime_type(file_path):
    return mimetypes.guess_type(file_path)[0] or 'application/octet-stream'

def made_uuid():
    return uuid.uuid4().hex
    
from multiprocessing import Manager
__mgr = Manager()
def ShareDict(*args, **kwargs):
    return __mgr.dict(*args, **kwargs)

from gale.version import is_py3
unicode_type = is_py3 and str or unicode

if is_py3:
    exec("""
def raise_exc_info(exc_info):
    raise exc_info[1].with_traceback(exc_info[2])

def exec_in(code, glob, loc=None):
    if isinstance(code, str):
        code = compile(code, '<string>', 'exec', dont_inherit=True)
    exec(code, glob, loc)
""")
else:
    exec("""
def raise_exc_info(exc_info):
    raise exc_info[0], exc_info[1], exc_info[2]

def exec_in(code, glob, loc=None):
    if isinstance(code, basestring):
        # exec(string) inherits the caller's future imports; compile
        # the string first to prevent that.
        code = compile(code, '<string>', 'exec', dont_inherit=True)
    exec code in glob, loc
""")
