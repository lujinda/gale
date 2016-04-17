#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2016-01-22 09:54:48
# Filename      : files.py
# Description   : 
from __future__ import print_function, unicode_literals

from gale import web


web.router('/dl(.*)', handler = web.FileHandler, 
        kwargs = {
            'root': '/data/', 
            'show_hidden': False,
            'hidden_list': [r'/.*?/gale/$'],
            'deny_hidden': True,
            'base_username': 'tuxpy',
            'base_password': 'zxc123',
            })

web.app_run(processes = 1)

