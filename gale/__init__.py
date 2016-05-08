#!/usr/bin/env python
#coding:utf8
# Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-25 13:19:19
# Filename        : __init__.py
# Description     : 
from __future__ import print_function

__ALL__ = ['version']
version = '4.7.6'


def run_env_check():
    import platform
    if platform.python_version() < '2.6':
        raise RuntimeError('python version must be >= 2.6')

    if platform.system() not in ('Linux', 'Darwin'):
        raise RuntimeError('gale not supported %s' %(platform.system()))

run_env_check()

