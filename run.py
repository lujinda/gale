#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-09 15:20:13
# Filename      : test.py
# Description   : 
from gale.web import app_run, router

@router(url = '/test', method='GET')
def test(self):
    print(self.get_signed_cookie('name'))
    self.set_signed_cookie('name', 'ljd')
    self.render('t.html', l = [1, 2, 3])

@router(url = '/test', method = 'POST')
def login_post(self):
    print(self.request.get_header('referer'))
    self.push('hello: ' + self.get_argument('firstname', '1') + " " +self.get_argument('lastname'))

app_run(__file__, settings = {'gzip': True, 'cookie_secret': '123'}, processes = 1)

