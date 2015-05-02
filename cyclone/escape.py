#/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-03-29 18:47:12
# Filename      : escape.py
# Description   : 
from cyclone.version import is_py3
from json import dumps


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

def param_encode(param):
    if is_py3:
        return param
    if isinstance(param, unicode):
        return param.encode('utf-8')

