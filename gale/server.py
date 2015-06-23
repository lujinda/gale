#!/usr/bin/env python
#coding:utf8
# Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-26 13:14:37
# Filename        : gale/server.py
# Description     : 
from __future__ import unicode_literals, print_function

try:
    from gale.stream import StreamServer
except ImportError as e:
    from gale.wsgi.stream import StreamServer

from multiprocessing import  cpu_count, Process

class HTTPServer(object):
    """
        http server
    """

    def __init__(self, callback, host = '0.0.0.0', port = 8080, timeout= 60, max_client = 1000):
        assert callable(callback) # callback必须是可调用的
        self.host = host
        self.port = port
        self._callback = callback # 表示回调函数
        self.timeout = timeout 
        self.max_client = max_client 

    def listen(self, port = 8080, host = ''):
        self.port = port
        self.host = host

    def run(self, processes = 0):
        _server = self.__made_server()
        if processes == 1: # 如果process值为1表示在主进程中执行
            self.__print_run_msg()
            _server.serve_forever()
        else:
            self.multi_run(server = _server, processes = processes)


    def __print_run_msg(self, processes = None):
        mess = "listen: http://%s:%s" % (self.host or '0.0.0.0', self.port)
        if processes:
            mess += ' processes: %d' % processes

        print(mess)

    def multi_run(self, server = None, processes = None):
        _server = server or self.__made_server()
        run_pool = []
        processes = processes or cpu_count() #  在此方法中，如未指定processes则是表示以cpu核数为限定
        for i in range(processes):
            p = Process(target = _server.serve_forever)
            run_pool.append(p)

        for p in run_pool: # 启动所有进程
            p.start()

        self.__print_run_msg(processes)

        for p in run_pool: # 等待
            p.join()

    def __made_server(self):
        return StreamServer((self.host, self.port), self._callback, 
                max_client = self.max_client, timeout = self.timeout)

