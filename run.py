#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-09 15:20:13
# Filename      : test.py
# Description   : 
from gale.web import app_run, router, RequestHandler, limit_referrer, HTTPError
from gale.cache import MemCacheManager, cache,  page

class CacheHandler(RequestHandler):
    @cache()
    def add(self, a, b):
        print('a + b')
        return a + b

    def on_connect_close(self):
        print('断开了')

    def load_js(self):
        return 'js'

    def load_css(self):
        return 'css'

@router(url = '/', method = 'GET')
def index(self):
    raise HTTPError(500)

@router(url = '/test', method='GET', base_handler = CacheHandler)
def test(self):
    self.render('t.html', l = [1, 2, 3])

@router(url = '/test', method = 'POST')
def login_post(self):
    self.push('hello: ' + self.get_argument('firstname', '1') + " " +self.get_argument('lastname'))

app_run(settings = {'debug': True, 'gzip': True, 'cookie_secret': '123', 'cache_manager': MemCacheManager(expire = 1000)}, processes = 1,  port = 5000)

