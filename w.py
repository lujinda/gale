#/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-11 15:52:19
# Filename      : w.py
# Description   : 
from gale.wsgi import WSGIApplication
from gale.web import RequestHandler
from wsgiref import simple_server

class IndexHandler(RequestHandler):
    def GET(self):
        counts = self.session.get('counts', 1)
        self.session['counts'] = counts + 1
        self.session.save()
        self.render('hello.html', counts = counts)

    def POST(self):
        print(self.get_file('file_b').body)

    def HEAD(self):
        print('ok')

app = WSGIApplication([
    (r'/', IndexHandler), ], settings = {
        'template': 'template',
        'static_path': 'static'})

server = simple_server.make_server('', 8080, app)
server.serve_forever()


