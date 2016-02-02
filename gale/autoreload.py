#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-07-05 13:38:30
# Filename      : autoreload.py
# Description   : 
import sys
import os
import signal
from gale import utils

modify_times = {}

def __check_modify(modify_times, path):
    try:
        st_mtime = os.stat(path).st_mtime
    except OSError:
        return

    if path not in modify_times: # 表示是新的
        modify_times[path] = st_mtime
        return 

    if modify_times[path] != st_mtime: # 表示已经有更新过了
        __reload_files()

def __reload_files():
    utils.stop_share_dict()
    os.execv(sys.executable, [sys.executable] + sys.argv)

def check_files():
    """检查文件的修改时间，检查对象是sys.path中的路径"""
    for module in sys.modules.values():
        path = getattr(module, '__file__', None)
        if not path:
            continue
        suffix = path.split('.')[-1]
        if suffix in ('pyc', 'pyo'):
            path = path[:-1]

        __check_modify(modify_times, path)

