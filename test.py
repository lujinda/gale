#!/usr/bin/env python
#coding:utf8
# Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-25 13:41:03
# Filename        : /home/ljd/py/coding/gale/test.py
# Description     : 
from gale.web import router, app_run, Application
from gale.session import FileSessionManager, RedisSessionManager
from redis import Redis

"""
class MyApplication(Application):
    def __init__(self):
        db = Redis()
        settings = {
                'debug' : True,
                'static_path'   :   'static',
                }

        self.session_manager = RedisSessionManager('aaaaa', 
                3, db)

        super(MyApplication, self).__init__(settings = settings)


app = MyApplication()
"""

@router(url='/hello')
def hello_get(self):
    counts = self.session.get('counts', 0)
    self.session['counts'] = counts + 1
    self.session.save()
    self.render('hello.html', counts = counts)

@router(url='/hello', method='POST')
def hello_post(self):
    print(self.request.all_arguments)
    print(self.request.files)

app_run()

"""

from gale.web import Application, RequestHandler
from gale.server import HTTPServer

class HelloHandler(RequestHandler):
    def GET(self):
        counts = self.session.get('counts', 0)
        self.session['counts'] = counts + 1
        self.session.save()
        self.render('hello.html', counts = counts + 1)

    def POST(self):
        print(self.request.all_arguments)

class MyApplication(Application):
    def __init__(self):
        handlers = [
                ('/hello', HelloHandler),
                ]
        settings = {
                'debug' : True,
                'static_path'   :   'static',
                }

        super(MyApplication, self).__init__(handlers, settings = settings)

http_server = HTTPServer(MyApplication())
http_server.listen(('', 8080))
http_server.run()

"""
