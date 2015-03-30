#!/usr/bin/env python
#coding:utf8
# Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-25 13:41:03
# Filename        : /home/ljd/py/coding/cyclone/test.py
# Description     : 
from cyclone.server import HTTPServer
from cyclone.web import Application, RequestHandler

class IndexHandler(RequestHandler):
    def POST(self):
        self.push(u"您的名字是%s" % (self.get_argument('name', 'ljd')))

class DemoApplication(Application):
    def __init__(self):
        handlers = [
                (r'/', IndexHandler),
                ]

        settings = {
                'debug'     :   True,
                }

        log_settings = {
                'level':    'DEBUG',
                }
        
        super(DemoApplication, self).__init__(handlers, 
                settings = settings, log_settings = log_settings)

server = HTTPServer(DemoApplication())
server.listen(('', 8000))
server.run()

