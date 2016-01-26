
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-03-29 18:47:12
# Filename      : escape.py
# Description   : 
from __future__ import unicode_literals
from gale.py_ver import is_py3
from json import dumps
import re

_XHTML_ESCAPE_RE = re.compile('[&<>"\']')
_XHTML_ESCAPE_DICT = {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;',                      '\'': '&#39;'}

long_type = is_py3 and int or long
unicode_type = is_py3 and str or unicode

def utf8(param):
    if is_py3:
        if isinstance(param, str):
            return param.encode()
    else:
        if isinstance(param, unicode):
            return param.encode('utf-8')

    return param

def param_decode(param):
    if is_py3:
        if isinstance(param, unicode_type):
            return param
        elif isinstance(param, bytes):
            return param.decode('utf-8')
        else:
            return param

    if isinstance(param, str):
        return param.decode('utf-8')

    return param


def to_unicode(param):
    param = param_decode(param)
    return param

def param_encode(param):
    if is_py3:
        return param
    if isinstance(param, unicode):
        return param.encode('utf-8')

if is_py3:
    native_str = to_unicode
else:
    native_str = utf8


def xhtml_escape(value):
    return _XHTML_ESCAPE_RE.sub(lambda match: _XHTML_ESCAPE_DICT[match.group(0)],
            to_unicode(value))

