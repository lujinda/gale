#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-11-27 10:06:12
# Filename      : load_balancer.py
# Description   : 
from __future__ import print_function, unicode_literals

import gevent
from gevent import socket
import threading
import argparse

import gale
from gale import (web, utils)
from . import strategy as strategy_module
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

class BalanceHandler(web.RequestHandler):
    pass

class WorkerCommandHandler(object):
    def __init__(self, strategy_manager):
        self.strategy_manager = strategy_manager

    def _execute(self, request):
        command = request['command']
        params = request['params']

        method = getattr(self, command, None)
        method(params)

    def login(self, params):
        print(params)

class BalanceServer(object):
    def __init__(self, listen_add, strategy_manager):
        self._socket = utils.get_gale_socket()

        self._socket.bind(listen_add)
        self._socket.listen(1024)

        self.strategy_manager = strategy_manager

    def serve_forver(self):
        while True:
            worker, addr = self._socket.accept()
            monitor_stream = MonitorStream(worker)
            try:
                gevent.spawn(self.start_monitor_worker(monitor_stream)) # Monitor the user to modify its own weight request
            except Exception as ex:
                print('get a exception in %s, error: %s' %(self.serve_forver, ex))
                pass

    def start_monitor_worker(self, monitor_stream):
        worker_command_handler = WorkerCommandHandler(self.strategy_manager)
        for request in monitor_stream.recv_request():
            print(request)
            worker_command_handler._execute(request)

class LoadBalancer(object):
    def __init__(self, password, host = '0.0.0.0', port = 1201, strategy = 'auto',
            upstream_settings = None):
        """
        strategy表示负载策略
        upstream_settings: 关于上游服务器的设置
            weight: 权重参数
        """
        if strategy not in ('auto', 'ip', 'round', 'weight'):
            raise gale.e.NotSupportStrategy('not support %s strategy' % (strategy))

        args = get_args_from_command()
        _password = args.password or password
        self.host = args.host or host
        self.port = args.port or port

        strategy = args.strategy or strategy
        self.strategy_manager = getattr(strategy_module, 
                "{strategy}StrategyManager".format(strategy = strategy.title()))(password, upstream_settings)

        t = threading.Thread(target = self.run)
        t.start()

    def run(self):
        balance_server = BalanceServer((self.host, self.port),
                self.strategy_manager)
        balance_server.serve_forver()

    def __call__(self, request, *args, **kwargs):
        handler = web.RequestHandler(web.Application(settings = {'gzip': False}),
                request)
        try:
            self.pass_request(handler)
        finally:
            handler.finish()
            self.strategy_manager.flush()

    def pass_request(self, handler):
        retry_counter = 0
        upstreams_total = self.strategy_manager.upstreams_total

        while True:
            try:
                self.strategy_manager.sort_upstreams_weight()
                upstream = self.strategy_manager.get_best_upstream(handler)
                if (not upstream) or retry_counter >= upstreams_total:
                    handler.set_status(502)
                    handler.set_header('Content-Type', 'text/html;charset=UTF-8')
                    handler.push(_BADGATEWAY_HTML)
                    return
                response = proxy_request(handler.request, upstream)
            except gale.e.WorkerOffline:
                retry_counter += 1
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

