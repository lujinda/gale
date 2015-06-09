
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-03-29 18:47:12
# Filename      : escape.py
# Description   : 
from __future__ import unicode_literals
from gale.version import is_py3
from json import dumps
import re

_XHTML_ESCAPE_RE = re.compile('[&<>"\']')
_XHTML_ESCAPE_DICT = {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;',                      '\'': '&#39;'}

def utf8(param):
    if is_py3:
        if isinstance(param, str):
            return param.encode()
    else:
        if isinstance(param, unicode):
            return param.encode('utf-8')
    if isinstance(param, (list, tuple, int, float, long)): # 如果参数不是字符串，则把它转成json·字符串，然后再utf8一下
        return utf8(dumps(param))

    return param

def param_decode(param):
    if is_py3:
        return param
    if isinstance(param, str):
        return param.decode('utf-8')

    return param

to_unicode = param_decode

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

