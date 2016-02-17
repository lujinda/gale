#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2016-02-17 14:19:43
# Filename      : files.py
# Description   : 
from __future__ import unicode_literals, print_function
import sys
import os
from gale import web

def get_share_path():
    try:
        share_path = sys.argv[1]
    except IndexError:
        share_path = os.getcwd()

    return os.path.abspath(share_path)

def share():
    web.router(r'/(.*)', handler = web.FileHandler,
            kwargs = {
                'root'      :       get_share_path(),
                })
            
    web.app_run(port = 8000, processes = 1)

if __name__ == "__main__":
    share()

