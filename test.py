#!/usr/bin/env python
#coding:utf8
# Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-25 13:41:03
# Filename        : /home/ljd/py/coding/cyclone/test.py
# Description     : 
from cyclone.server import HTTPServer
from cyclone.web import Application, RequestHandler
from cyclone.e import HTTPError
from functools import wraps

from redis import Redis

def contorl_access(method):
    @wraps(method)
    def wrap(self, *args, **kwargs):
        _ip = 'contorl_access:' + self.client_ip
        _num = int(self.db.get(_ip) or 0)
        _num = self.db.incr(_ip)
        if _num > 5: # 在规定时间里最多只允许访问 5次
            raise HTTPError(503)

        if _num == 1: # 如果是第一次访问，则设置过期时间
            self.db.expire(_ip, 5)
        return method(self, *args, **kwargs)
    return wrap

class IndexHandler(RequestHandler):
    def GET(self, name = 'abc'):
        self.render('index.html')

    def POST(self):
        print(self.request.all_arguments)

    @property
    def db(self):
        return self.application.db

    def HEAD(self, name="abc"):
        self.push('ok')


class LoginHandler(RequestHandler):
    def GET(self):
        self.redirect('/test')

class DemoApplication(Application):
    def __init__(self):
        handlers = [
                (r'/login', LoginHandler),
                (r'/test', IndexHandler),
                ]


        settings = {
                'debug'     :   True,
                'real_ip'   :   True,
                }
        vhost_handlers = [
                (r'^localhost.*', handlers),
                ]

        log_settings = {
                'level':    'DEBUG',
                }
        template_settings = {
                'template_path': 'template',
                }


        self.db = Redis()

        super(DemoApplication, self).__init__(vhost_handlers = vhost_handlers, 
                settings = settings, log_settings = log_settings,
                template_settings = template_settings)

server = HTTPServer(DemoApplication())
server.listen(('', 8000))
server.run(processes = 4)

