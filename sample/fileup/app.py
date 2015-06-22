#/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-22 11:00:56
# Filename      : app.py
# Description   : 
from gale.web import Application
from index import IndexHandler, FileHandler
import os

class MyApplication(Application):
    def __init__(self):
        handlers = [
                (r'/', IndexHandler), 
                (r'/file', FileHandler), 
                ]

        settings = {
                'debug' : True,
                'static_path'   : os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                    'static'),
                'template_path'  :  os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                    'template'),
                }

        super(MyApplication, self).__init__(handlers, 
                settings = settings)

