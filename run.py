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
    print('共有 %s 个进程 ' % (self.server_settings['processes']))
    self.render('t.html', l = [1, 2, 3])

@router(url = '/test', method = 'POST')
def login_post(self):
    self.push('hello: ' + self.get_argument('firstname', '1') + " " +self.get_argument('lastname'))

@router(url = '/down', method = 'GET')
def down(self):
    print(self.request.headers)
    # self.send_file('/data/iso/CentOS.6.4.iso', speed = 1024 * 40)
    self.send_file('/data/HTTP权威指南完整版.pdf', speed = 1024  * 1024 * 1024 * 10)

@router(url = '/login', method = 'GET')
def login(self):
    """
    restapi: 查询某个用户是否登录
    username|用户名
    """ 
    print(self.request.uri)
    print(self.request.all_arguments)

@router(url = '/login', method = 'POST')
def login_post(self):
    """
    restapi: 用户登录
    username | 用户
    password | 密码
    """
    self.push(self.body.username)


app_run(settings = {'debug': True, 'gzip': False, 'cookie_secret': '123', 'cache_manager': MemCacheManager(expire = 1000)}, processes = 1,  port = 5000)

