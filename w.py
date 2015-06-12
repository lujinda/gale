#/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-11 15:52:19
# Filename      : w.py
# Description   : 
from __future__ import unicode_literals
from gale.web import RequestHandler, Application, auth_401
from gale.server import HTTPServer

application = Application(settings = {
        'template': 'template',
        'static_path': 'static'})

@application.router(url=r'/')
@auth_401
def index(self):
    self.render('hello.html', counts = "总数")

@application.router(url=r'/', method = 'post')
def post(self):
    print(self.request.all_arguments)
    print(self.request.files)

application.run()


# uwsgi --http :8080 --wsgi-file w.py  --master --processes 4 

