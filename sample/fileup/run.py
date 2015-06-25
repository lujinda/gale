#/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-22 10:58:32
# Filename      : run.py
# Description   : 
from gale.server import HTTPServer
from app import MyApplication
import sys

def get_port():
    if len(sys.argv) < 2:
        return 8000
    port = sys.argv[1]
    if not port.isdigit():
        port = 8000
    return int(port)

server = HTTPServer(MyApplication())
server.listen(get_port())
server.run()

