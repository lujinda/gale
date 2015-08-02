#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-11 15:52:19
# Filename      : w.py
# Description   : 

from gale.web import router, app_run

@router('/')
def send_file(self):
    self.send_file('/etc/passwd', md5 = True)

app_run()

