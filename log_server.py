#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com # Last modified : 2015-07-11 11:16:37
# Filename      : log_server.py
# Description   : 
from gale.web import router, app_run
import re
re_float = re.compile(r'^\d*\.\d*$')
re_int = re.compile(r'^\d*\d$')

def parse_value(v):
    if re_float.match(v):
        return float(v)
    elif re_int.match(v):
        return int(v)
    elif v == 'None':
        return None

    return v

@router(r'/log', method = 'POST')
def log(self):
    log_dict = {}
    for _k, _v in self.request.all_arguments.items():
        if len(_v) == 1:
            log_dict[_k] = parse_value(_v[0])
        else:
            for __v in _v:
                log_dict.setdefault(_k, []).append(parse_value(__v))

    print(self.request.all_arguments)

app_run(port = 8009)

