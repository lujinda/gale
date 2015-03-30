#!/usr/bin/env python
#coding:utf8
# Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-25 14:18:30
# Filename        : cyclone/e.py
# Description     : 

class HeaderFormatError(Exception):
    pass

class NotSupportMethod(Exception):
    status_code = 405

class ErrorStatusCode(Exception):
    pass

class MissArgument(Exception):
    pass

