#/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-11 15:52:19
# Filename      : w.py
# Description   : 
from __future__ import unicode_literals
from gale.web import RequestHandler, Application, auth_401
from gale.wsgi.web import WSGIApplication
from gale.server import HTTPServer

application = Application(settings = {
    'debug' :   True,
        'template': 'template',
        'static_path': 'static',
        'gzip':True,
        })

@application.router(url=r'/', method = 'post')
def post(self):
    print(self.request.headers)
    print(self.request.body)
    print(self.request.all_arguments)
    print(self.request.files)

@application.router(url=r'/', method='get', kwargs = {'hi': 'def'})
#@auth_401
def index(self):
    print(self.kwargs)
    self.render('hello.html', counts = "总数")


application.run()

# uwsgi --http :8080 --wsgi-file w.py  --master --processes 4 

