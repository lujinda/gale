#coding:utf8
from gale.web import  router, app_run
from gale.server import HTTPServer
from gale.ipc import IPCDict
import os

@router(url='/')
def index(self):
    ipc_dict = IPCDict('counter')
    access_counter = ipc_dict.incr('access_counter')
    self.push("pid: %s counter:%s" % (os.getpid(), access_counter))

app_run(processes = 4)

