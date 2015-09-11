#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-09-08 14:16:41
# Filename      : wsocket.py
# Description   : 
from __future__ import print_function
from gale.websocket import WebSocketHandler
from gale.web import Application, RequestHandler
from gale.server import HTTPServer

clients = set()


class ConnHandler(WebSocketHandler):
    def on_open(self):
        print('有人连接了')

    def on_close(self, code, reason):
        print(code, reason)
        print('有人走了')

app = Application(handlers = [
    (r'/conn', ConnHandler),
    ], settings = {'debug': True})

@app.router(url = '/')
def index(self):
    self.render('websocket.html')

http_server = HTTPServer(app)
http_server.listen(5005)
http_server.run(processes = 1)

