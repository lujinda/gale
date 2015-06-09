#!/usr/bin/env python
#coding:utf8
# Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-26 13:14:37
# Filename        : gale/server.py
# Description     : 
from __future__ import unicode_literals, print_function

import gevent
from gale.stream import StreamServer
from multiprocessing import  cpu_count, Process

class HTTPServer(object):
    """
        http server
    """
    listen_add = (None, None)

    def __init__(self, callback, listen_add = (None, None), timeout= 60, max_client = 1000):
        assert callable(callback) # callback必须是可调用的
        self._callback = callback # 表示回调函数
        self.timeout = timeout 
        self.listen(listen_add)
        self.max_client = max_client 

    def listen(self, listen_add):
        self.listen_add = listen_add

    def run(self, listen_add = None, processes = 0):
        _server = self.__made_server(listen_add)
        if processes == 1: # 如果process值为1表示在主进程中执行
            self.__print_run_msg()
            _server.serve_forever()
        else:
            self.multi_run(server = _server, processes = processes)


    def __print_run_msg(self, processes = None):
        mess = "listen: http://%s:%s" % (self.host, self.port)
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

    def __made_server(self, listen_add = None):
        if isinstance(listen_add, (tuple, list)):
            self.listen(listen_add)
        return StreamServer(self.listen_add, self._callback, 
                max_client = self.max_client, timeout = self.timeout)

    @property
    def port(self):
        return self.listen_add[1]

    @property
    def host(self):
        return self.listen_add[0] or '0.0.0.0'

