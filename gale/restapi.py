#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-09-25 16:09:31
# Filename      : restapi.py
# Description   : 
from __future__ import unicode_literals, print_function
import re
from gale.escape import to_unicode

_ALL_METHOD = ('POST', 'GET', 'PUT', 'DELETE', 'HEAD')
re_resetapi_flag = re.compile(r'^rest\s*api:')

class RestApi(object):
    def __init__(self, handlers):
        self.vhost_handlers = handlers

    def __get_all_handlers(self):
        """把所有的handlers以及相关的url列出来"""
        handlers = {}
        host_map = {'.*': '*'}
        for _host, _handlers in self.vhost_handlers:
            _host = _host.pattern[1: -1]
            _host = host_map.get(_host, _host)
            for re_url, _handler, kwargs in _handlers:
                handlers.setdefault(_host, []).append((re_url.pattern[1: -1],
                    _handler))

        return handlers

    def generate_restapi_list(self):
        all_handlers = self.__get_all_handlers()
        api_handlers = {}
        for host in all_handlers:
            handlers = all_handlers[host]
            _api_handlers = []
            for url, handler in handlers:
                _api_handler = self.genearte_resetapi_info(handler)
                if not _api_handler: # 表示该handler不包含reset api信息
                    continue
                api_handlers.setdefault(host, []).append((url, _api_handler))

        return api_handlers

    def genearte_resetapi_info(self, handler):
        """生成api处理类各方法的信息"""
        handler_info = {} # 这是整个处理类的
        for method in _ALL_METHOD:
            method_handler = getattr(handler, method)
            if not self.is_resetapi_method(method_handler):
                continue
            method_info = self.parse_method_doc(to_unicode(method_handler.__doc__))
            handler_info[method] = method_info

        return handler_info

    def parse_method_doc(self, doc):
        lines = [line.strip() for line in doc.split('\n') if line.strip()] # 去掉了空行和每一行的前后空字符
        description = lines[0].split(':')[1].strip()
        _params = []
        for line in lines[1:]:
            try:
                _parts = ([ _t.strip() for _t in line.split('|')] + ['string'])[:3] # 格式:  参数名|参数描述[|参数类型]
                param_name, param_desc, param_type = _parts
                _params.append((param_name, param_desc, param_type))
            except ValueError:
                continue

        return _params

    def is_resetapi_method(self, method):
        """通过解析method的__doc__来得出这是不是个rest api"""
        doc = to_unicode((method.__doc__ or '').strip())
        if doc == '':
            return False
        return bool(re_resetapi_flag.match(doc))

