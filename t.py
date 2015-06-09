#/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-09 09:44:05
# Filename      : t.py
# Description   : 
from gale.cache import MemCacheModel
import time

cache_model = MemCacheModel()

def cache(func):
    def wrap(*args, **kwargs):
        cache = cache_model.get('test')
        if cache:
            return cache
        _result = func(*args, **kwargs)
        cache_model.set('test', _result, 3)
        return _result

    return wrap

@cache
def func(a, b):
    print('a+b')
    return a + b

print(func(1, 2))
time.sleep(2)
print(func(1, 2))

