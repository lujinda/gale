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

class IndexHandler(RequestHandler):
    def GET(self):
        self.render('websocket.html')

class ConnHandler(WebSocketHandler):
    def on_open(self):
        for client in clients:
            client.send_message('有朋友连接上来了')
        clients.add(self)

    def on_close(self):
        clients.remove(self)

app = Application(handlers = [
    (r'/conn', ConnHandler),
    (r'/', IndexHandler),
    ], settings = {'debug': True})
http_server = HTTPServer(app)
http_server.listen(5005)
http_server.run(processes = 1)

