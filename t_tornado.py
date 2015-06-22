#/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-22 12:47:10
# Filename      : t_tornado.py
# Description   : 
from tornado.web import Application, RequestHandler
from tornado.ioloop import IOLoop
class THandler(RequestHandler):
    def get(self):
        self.render('t.html', l = [1, 2, 3])

app = Application([('/test', THandler)], static_path = 'static', template_path = 'template')
app.listen(8080)
IOLoop.instance().start()

