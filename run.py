#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-09 15:20:13
# Filename      : test.py
# Description   : 
from gale.web import app_run, router, RequestHandler, limit_referrer, HTTPError
from gale.cache import MemCacheManager, cache,  page
from gale.balance import LoadWorker

API_MODULE_DOC = '测试用'

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
    self.res_body + 'ok'

def load_js(self):
    return 'js'

@router(url = '/test', method='GET', 
        bind_methods = {'load_js': load_js})
def test(self):
    print('共有 %s 个进程 ' % (self.server_settings['processes']))
    self.render('t.html', l = [1, 2, 3])

@router(url = '/test', method = 'POST')
def login_post(self):
    self.push('hello: ' + self.get_argument('firstname', '1') + " " +self.get_argument('lastname'))

@router(url = '/down', method = 'GET')
def down(self):
    print(self.request.headers)
    #self.send_file('/data/iso/CentOS.6.4.iso', speed = 1024  * 100)
    self.send_file('/data/HTTP权威指南完整版.pdf', speed =  1024 * 100)

@router(url = '/login', method = 'GET')
def login(self):
    """
    restapi: 查询某个用户是否登录
    request:
        username:用户名
    """ 
    print(self.request.uri)
    print(self.request.all_arguments)

@router(url = '/login', method = 'POST')
def login_post(self):
    """
    restapi: 用户登录
    request:
        username: 用户
        password: 密码
    """
    self.push(self.body.username)


def get_port():
    import sys
    if len(sys.argv) < 2:
        return 5000

    if sys.argv[1].isdigit():
        return int(sys.argv[1])

    return 5000

load_worker = LoadWorker(target_host = '127.0.0.1', password = '123', reconnect_interval = 5)
app_run(settings = {'debug': True, 'gzip': False, 'cookie_secret': '123', 'cache_manager': MemCacheManager(expire = 1000)}, processes = 1,  port = get_port(), server_settings = {'load_worker': load_worker})

