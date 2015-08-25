#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-11 15:52:19
# Filename      : w.py
# Description   : 

from gale.web import router, app_run, RequestHandler, async
from gale.coroutine import coroutine
import time
import urllib2

class BaseHandler(RequestHandler):
    def on_result(self, result, e):
        self.push(result)
        self.finish()

    @coroutine
    def get_html(self, url):
        content = ''
        time.sleep(10)
        raise Exception()
        for i in range(5):
            content = urllib2.urlopen(url).read()
        return content

@router('/', base_handler = BaseHandler)
@async
def send_file(self):
    self.get_html('http://www.zjycloud.com')

@router('/test')
def send_file(self):
    self.push('test')

app_run(processes = 1)

