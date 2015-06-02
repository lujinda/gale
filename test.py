#!/usr/bin/env python
#coding:utf8
# Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-25 13:41:03
# Filename        : /home/ljd/py/coding/gale/test.py
# Description     : 
from gale.web import router, app_run, Application, RequestHandler
from gale.server import HTTPServer

@router(url='/hello')
def hello_get(self):
    self.render('hello.html')

@router(url='/hello', method='POST')
def hello_post(self):
    pass

app_run()

"""

class HelloHandler(RequestHandler):
    def GET(self):
        self.render('hello.html')

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
