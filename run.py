#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-09 15:20:13
# Filename      : test.py
# Description   : 
from gale.web import app_run, router, RequestHandler, limit_referrer
from gale.cache import MemCacheManager, cache,  page

class CacheHandler(RequestHandler):
    @cache()
    def add(self, a, b):
        print('a + b')
        return a + b

@router(url = '/test', method='GET', base_handler = CacheHandler)
@limit_referrer
@page(expire = 10)
def test(self):
    self.render('t.html', l = [1, 2, 3])

@router(url = '/test', method = 'POST')
def login_post(self):
    print(self.request.all_arguments)
    self.push('hello: ' + self.get_argument('firstname', '1') + " " +self.get_argument('lastname'))

app_run(__file__, settings = {'gzip': True, 'cookie_secret': '123', 'cache_manager': MemCacheManager(expire = 10)}, processes = 1)

