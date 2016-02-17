#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-11-27 11:00:52
# Filename      : worker.py
# Description   : 
from __future__ import print_function, unicode_literals
from gale import utils


class LoadWorker(object):
    def __init__(self, target_host, password, target_port = 1201):
        self.target_host = target_host
        self.target_port = target_port
        self.password = password
        self._socket = utils.get_gale_socket()

    def run(self):
        pass

