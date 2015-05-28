#!/usr/bin/env python
#coding:utf8
# Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-25 13:41:03
# Filename        : /home/ljd/py/coding/cyclone/test.py
# Description     : 
from cyclone.web import router, app_run

@router(url='/hello')
def hello(self):
    self.push('hi')

app_run()

