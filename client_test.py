#!/usr/bin/env python
#coding:utf8
# Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-25 16:05:01
# Filename        : client_text.py
# Description     : 
from requests import post, get

print (post('http://127.0.0.1:8000', data={'name': 'ljy'}).text)

