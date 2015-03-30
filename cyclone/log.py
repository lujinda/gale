#/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-03-30 18:06:49
# Filename      : log.py
# Description   : 
from __future__ import unicode_literals
import logging

access_log = logging.getLogger('access_log')

def config_logging(log_settings):
    """配置logging"""
    console = logging.StreamHandler()
    console.setLevel(getattr(logging, log_settings.get('level', 'DEBUG'),
            logging.DEBUG))
    formatter = logging.Formatter('%(asctime)s %(filename)s [%(process)d] %(levelname)s %(message)s',
            datefmt = log_settings.get('datefmt', '%Y-%m-%d %H:%M:%s'))

    console.setFormatter(formatter)
    access_log.addHandler(console)
    access_log.setLevel(console.level) # 如果只是addHandler的话access_log的日志等级是没有被设置过的，也就默认的WARNING

