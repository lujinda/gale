#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-03-30 18:06:49
# Filename      : log.py
# Description   : 
from __future__ import unicode_literals
import logging
import re

access_log = logging.getLogger('access_log')
gen_log = logging.getLogger('gen_log')

class ColorLogFormatter(logging.Formatter):
    COLOR_CODE = {logging.INFO: '32',
            logging.WARNING: '33',
            logging.ERROR: '31'}

    def __init__(self, fmt = None, datefmt = None):
        logging.Formatter.__init__(self, fmt, datefmt)
        self._raw_fmt = fmt
        self._re_fmt = re.compile(r'(%\(\w+?\)\w)')

    def format(self, record):
        def generate_color_str(m):
            color_str = "\x1b[0;{color};1m{arg}\x1b[0m".format(color = self.COLOR_CODE[record.levelno], arg = m.group(1))
            return color_str

        self._fmt = self._re_fmt.sub(generate_color_str, 
                self._raw_fmt, count = 1)
        return logging.Formatter.format(self, record)

def config_logging(log_settings):
    """配置logging"""
    save_file = log_settings.get('file')
    stream_handler = logging.StreamHandler()
    handler_list = [stream_handler]
    if save_file:
        file_handler = logging.FileHandler(save_file)
        handler_list.append(file_handler)
    for _handler in handler_list:
        _handler.setLevel(getattr(logging, log_settings.get('level', 'DEBUG'),
            logging.DEBUG))
        formatter_class = isinstance(_handler, logging.StreamHandler) and ColorLogFormatter or logging.Formatter
        formatter = formatter_class('%(asctime)s %(filename)s [%(process)d] %(levelname)s %(message)s',
                datefmt = log_settings.get('datefmt', '%Y-%m-%d %H:%M:%S'))

        _handler.setFormatter(formatter)
        access_log.addHandler(_handler)
    access_log.setLevel(stream_handler.level) # 如果只是addHandler的话access_log的日志等级是没有被设置过的，也就默认的WARNING
    gen_log.setLevel(stream_handler.level) 

    if 'request_format' in log_settings:
        access_log.request_format = log_settings['request_format']

def generate_request_log(handler):
    log_format_string = getattr(access_log, 'request_format',
            '{start_timestamp} {first_line} {status_code} {client_ip} {request_time}')

    request = handler.request

    return log_format_string.format(
            start_timestamp = request.start_time,
            method = request.method,
            uri = request.uri,
            path = request.path,
            client_ip = request.client_ip,
            status_code = handler.get_status(),
            first_line = request.first_line,
            version = request.version,
            body_size = request.size,
            response_size = handler.get_been_set_header('Content-Length'),
            request_time = "%.2fms" % (request.request_time * 1000, ),
            )

