#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-08-25 19:59:30
# Filename      : coroutine.py
# Description   : 
import gevent
from gevent import Greenlet, monkey
from functools import wraps

class Coroutine(Greenlet):
    def __init__(self, func, args = None, kwargs = None, callback = None):
        Greenlet.__init__(self)
        self._args = args or ()
        self._kwargs = kwargs or {}
        self._callback = callback
        self._func = func

    def _run(self):
        error = None
        result = None
        try:
            result = self._func(*self._args, **self._kwargs)
        except Exception as e:
            error = e

        if self._callback:
            self._callback(result, error)


def coroutine(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        monkey.patch_all()
        callback = kwargs.pop('callback', None)
        _coroutine = Coroutine(func, args, kwargs,
                callback = callback)
        _coroutine.start()

    return wrap
