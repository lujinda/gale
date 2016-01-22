#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-09 10:04:55
# Filename      : setup.py
# Description   : 
from setuptools import setup
from gale import version
setup(
        name = 'gale_web',
        version = version,
        author = 'tuxpy',
        url = 'https://github.com/lujinda/gale',
        include_package_data = True,
        packages = [
            'gale',
            'gale.wsgi',
            ],
        install_requires = ['gevent', 'msgpack-python'],
        description = 'a web framework like tornado',
        )


