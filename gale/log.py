#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-03-30 18:06:49
# Filename      : log.py
# Description   : 
from __future__ import unicode_literals
import logging

access_log = logging.getLogger('access_log')
gen_log = logging.getLogger('gen_log')

def config_logging(log_settings):
    """配置logging"""
    save_file = log_settings.get('file')
    stream_handler = logging.StreamHandler()
    handler_list = [stream_handler]
    if save_file:
        file_handler = logging.FileHandler(save_file)
        handler_list.append(file_handler)
    for _handler in handler_list:
        _handler.setLevel(getattr(logging, log_settings.get('level', 'DEBUG'),
            logging.DEBUG))
        formatter = logging.Formatter('%(asctime)s %(filename)s [%(process)d] %(levelname)s %(message)s',
                datefmt = log_settings.get('datefmt', '%Y-%m-%d %H:%M:%s'))

        _handler.setFormatter(formatter)
        access_log.addHandler(_handler)
    access_log.setLevel(stream_handler.level) # 如果只是addHandler的话access_log的日志等级是没有被设置过的，也就默认的WARNING
    gen_log.setLevel(stream_handler.level) 

