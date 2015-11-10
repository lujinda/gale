#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-09-25 16:09:31
# Filename      : restapi.py
# Description   : 
from __future__ import unicode_literals, print_function
import re
from gale import e
from gale.escape import to_unicode

__all__ = ['RestApi']

_ALL_METHOD = ('POST', 'GET', 'PUT', 'DELETE', 'HEAD')
re_resetapi_flag = re.compile(r'^rest\s*api:')

class DocParser(object):
    def __init__(self, raw_data = None):
        self.raw_data = raw_data

    def is_space_line(self, line):
        return not line.strip()

    def parse(self, raw_data = None):
        raw_data = raw_data or self.raw_data
        if not raw_data:
            return raw_data

        current_fork = tree = {}
        parent_line = None
        last_node = None

        for line in raw_data.split('\n'):
            if self.is_space_line(line):
                continue
            key, value = self.parse_line(line)

            if parent_line and self.entry_child_node(line, parent_line):
                current_fork[key] = value
            else:
                if last_node and (not current_fork):
                    tree[last_node] = self.parse_line(parent_line)[1]
                current_fork = tree.setdefault(key, {})
                last_node = key
                parent_line = line

        return tree

    def entry_child_node(self, line, last_line):
        return self.get_line_indent(line) > self.get_line_indent(last_line)

    def get_line_indent(self, line):
        return len(line) - len(line.strip())

    def parse_line(self, line):
        if ':' in line:
            return [item.strip() for item in line.split(':', 1)]
        else:
            raise e.DocParserError("':' must in line")

def parse_doc(raw_doc):
    if not raw_doc:
        return None
    doc_parser = DocParser(raw_doc)
    return doc_parser.parse()

class RestApi(object):
    def __init__(self, handlers):
        self.vhost_handlers = handlers

    def __get_all_handlers(self):
        """把所有的handlers以及相关的url列出来"""
        handlers = []
        for _host, _handlers in self.vhost_handlers:
            for re_url, _handler, kwargs in _handlers:
                handlers.append((re_url.pattern[1: -1],
                    _handler))

        return handlers

    def generate_restapi_list(self):
        all_handlers = self.__get_all_handlers()
        all_api_handlers = {}
        for url, handler in all_handlers:
            _api_handler_info = self.genearte_resetapi_info(handler)
            if not _api_handler_info: # 表示该handler不包含reset api信息
                continue

            module_name = handler.__module__
            _module = __import__(module_name, fromlist = [module_name])
            module_doc = getattr(_module, 'API_MODULE_DOC', None)
            if module_doc:
                module_name += '(%s)' % (to_unicode(module_doc), )

            all_api_handlers.setdefault(module_name,
                    []).append((url, handler, _api_handler_info))

        return all_api_handlers

    def genearte_resetapi_info(self, handler):
        """生成api处理类各方法的信息"""
        handler_api_doc = []
        for method in _ALL_METHOD:
            method_handler = getattr(handler, method, None)
            if not (method_handler and self.is_resetapi_method(method_handler)):
                continue
            api_method_doc = self.parse_method_doc(to_unicode(method_handler.__doc__))
            api_method_doc['method'] = method
            handler_api_doc.append(api_method_doc)

        return handler_api_doc

    def parse_method_doc(self, doc):
        return parse_doc(doc)

    def is_resetapi_method(self, method):
        """通过解析method的__doc__来得出这是不是个rest api"""
        doc = to_unicode((method.__doc__ or '').strip())
        if doc == '':
            return False
        return bool(re_resetapi_flag.match(doc))

