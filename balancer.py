#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-11-27 10:07:28
# Filename      : balancer.py
# Description   : 
from __future__ import print_function, unicode_literals

from gale.balance import LoadBalancer
from gale import server
from gale.web import Application

load_balancer = LoadBalancer(strategy = 'ip', password = '123', 
        upstream_settings = {
            'hosts': ['127.0.0.1:5000', '127.0.0.1:5001'],
            })
server = server.HTTPServer(load_balancer)
server.run(processes = 1)

