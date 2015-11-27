#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-11-27 10:06:12
# Filename      : load_balancer.py
# Description   : 
from __future__ import print_function, unicode_literals

import gevent
import threading
import argparse

import gale
from gale import web
from . import strategy as _strategy
from .request import proxy_request

__all__ = ['LoadBalancer']

def get_args_from_command():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', dest = 'strategy', help = 'load balancing strategy')
    parser.add_argument('-H', dest = 'host', help = 'load balancing listening host')
    parser.add_argument('-p', dest = 'port', help = 'load balancing listening port')
    parser.add_argument('-P', dest = 'password', help = 'load balancing worker connect password')

    args = parser.parse_args()

    return args

_BADGATEWAY_HTML = """
<html>
<title>Bad Gateway</title>
<body>
<center><h1>Bad Gateway</h1></center>
</body>
</html>
"""

class LoadBalancer(object):
    def __init__(self, password, host = '0.0.0.0', port = 1201, strategy = 'auto', 
            upstream_settings = None):
        """
        strategy表示负载策略
        upstream_settings可以提供上流服务器的参数,如指定ip地址等
        """
        if strategy not in ('auto', 'ip', 'round', 'weight'):
            raise gale.e.NotSupportStrategy('not support %s strategy' % (strategy))

        args = get_args_from_command()
        self.password = args.password or password
        self.host = args.host or host
        self.port = args.port or port

        strategy = args.strategy or strategy
        self.strategy_manager = getattr(_strategy, 
                "{strategy}StrategyManager".format(strategy = strategy.title()))(upstream_settings)

    def run(self):
        print('strategy manager is ', self.strategy_manager)

    def __call__(self, request, *args, **kwargs):
        handler = web.RequestHandler(web.Application(settings = {'gzip': False}),
                request)
        try:
            self.pass_request(handler)
        finally:
            handler.finish()

    def pass_request(self, handler):
        while True:
            try:
                upstream = self.strategy_manager.get_best_upstream()
                if not upstream:
                    handler.set_status(502)
                    handler.set_header('Content-Type', 'text/html;charset=UTF-8')
                    handler.push(_BADGATEWAY_HTML)
                    return
                response = proxy_request(handler.request, upstream)
            except gale.e.WorkerOffline:
                self.strategy_manager.add_invalid_upstream(upstream)
                continue
            else:
                break

        handler.set_status(response.status, response.reason)
        handler.clear_headers()
        handler.push(response.read())

        for key, values in response.getheaders():
            for value in values.split(', '):
                handler.add_header(key, value.lstrip())

