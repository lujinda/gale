#/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-22 10:58:32
# Filename      : run.py
# Description   : 
from gale.server import HTTPServer
from app import MyApplication

server = HTTPServer(MyApplication())
server.listen(8080)
server.run()

