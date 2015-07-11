#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com # Last modified : 2015-07-11 11:16:37
# Filename      : log_server.py
# Description   : 
from gale.web import router, app_run
import re
import ast
import logging

re_float = re.compile(r'^\d*\.\d*$')
re_int = re.compile(r'^\d*\d$')
re_tuple = re.compile(r'^\(.*\)$')

def get_logger():
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(lineno)s %(levelname)s %(message)s", datefmt = "%Y-%m-%d %H:%M:%s")
    handler.setFormatter(formatter)

    logger = logging.getLogger('test')
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


    return logger

def parse_value(v):
    if re_float.match(v):
        return float(v)
    elif re_int.match(v):
        return int(v)
    elif re_tuple.match(v):
        return ast.literal_eval(v)
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

    log_record = logging.makeLogRecord(log_dict)
    logger = get_logger()
    logger.handle(log_record)

app_run(port = 8009)

