#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-09 15:20:13
# Filename      : test.py
# Description   : 
from gale.web import app_run, router, RequestHandler
from gale.cache import MemCacheManager, cache, RedisCacheManager, page
from redis import Redis

db = Redis()

class CacheHandler(RequestHandler):
    @cache(on='redis')
    def add(self, a, b):
        print('a + b')
        return a + b

@router(url = '/test', method='GET', base_handler = CacheHandler)
@page(expire = 10)
def test(self):
    print(self.add(1, 2))
    self.render('t.html', l = [1, 2, 3])

@router(url = '/test', method = 'POST')
def login_post(self):
    print(self.request.get_header('referer'))
    self.push('hello: ' + self.get_argument('firstname', '1') + " " +self.get_argument('lastname'))

app_run(__file__, settings = {'gzip': True, 'cookie_secret': '123', 'cache_manager': [RedisCacheManager(expire = 10, db = db), 
    MemCacheManager(expire = 10)]}, processes = 1)

