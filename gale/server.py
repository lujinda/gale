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

from gale.ipc import IPCServer
import atexit

from multiprocessing import  cpu_count, Process

class ServerSettings(dict):
    def __new__(self, *args, **kwargs):
        if hasattr(ServerSettings, '_instance'):
            return ServerSettings._instance
        instance = dict.__new__(self, *args, **kwargs)
        ServerSettings._instance = instance

        return ServerSettings._instance

    def __setattr__(self, name, value):
        self[name] = value

    def __getattr__(self, name):
        try:
             return self[name]
        except KeyError:
             raise

class HTTPServer(object):
    """
        http server
    """
    def __init__(self, callback, host = '0.0.0.0', port = 8080, timeout = 15, max_client = 1000, autoreload = True,
            load_worker = None):
        assert callable(callback) # callback必须是可调用的
        self.host = host
        self.port = port
        self._callback = callback # 表示回调函数
        self.autoreload = autoreload
        self.run_pool = []
        if load_worker: # 如果有load worker则需要将它连接到主控制器中
            load_worker.run()
        self.settings = ServerSettings(processes = 0, timeout = timeout,
                        max_client = max_client)

        atexit.register(self.stop)

    def listen(self, port = 8080, host = ''):
        self.port = port
        self.host = host

    def run(self, processes = 0):
        try:
            self._run(processes)
            for p in self.run_pool:
                p.join()
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        for p in self.run_pool:
            p.terminate()

    def _run(self, processes = 0):
        processes = processes or cpu_count() 
        self.settings.processes = processes
        if self.autoreload and processes != 1:  # 自动重载不支持多进程模式，自动关闭自动重载
            self.autoreload = False
            print("autoreload not suport multi procesess")

        _server = self.__made_server()
        if processes == 1: # 如果process值为1表示在主进程中执行
            self.__print_run_msg()
            _server.serve_forever()
        else:
            self._multi_run(server = _server, processes = processes)

            ipc_server = IPCServer()
            ipc_server.serve_forever()

    def __print_run_msg(self, processes = None):
        mess = "listen: http://%s:%s" % (self.host or '0.0.0.0', self.port)
        if processes:
            mess += ' processes: %d' % processes

        print(mess)

    def _multi_run(self, server = None, processes = None):
        _server = server or self.__made_server()
        processes = processes or cpu_count() #  在此方法中，如未指定processes则是表示以cpu核数为限定
        for i in range(processes):
            p = Process(target = _server.serve_forever, args = (True, ))
            self.run_pool.append(p)

        for p in self.run_pool: # 启动所有进程
            p.start()

        self.__print_run_msg(processes)

    def __made_server(self):
        return StreamServer((self.host, self.port), self._callback, 
                 autoreload = self.autoreload, settings = self.settings)

