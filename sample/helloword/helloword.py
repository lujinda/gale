#/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-09 10:03:05
# Filename      : helloword.py
# Description   : 
from gale.web import router, app_run

"""
@router(url = r'/(\w+)?', host='localhost', method = 'GET')
def hello(self, name = None):
    self.push('hello ' + (name or 'XXX'))

app_run()

"""
# 下面这样也可以哦

from gale.web import Application, RequestHandler
from gale.server import HTTPServer

class HelloHandler(RequestHandler):
    def GET(self, name = None):
        self.push('hello ' + (name or 'XXX'))

app = Application(handlers = [(r'/(\w+)?', HelloHandler), ])
http_server = HTTPServer(app)
http_server.listen(8080)
http_server.run()
