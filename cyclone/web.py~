#!/usr/bin/env python
#coding:utf8
# Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-26 13:16:41
# Filename        : cyclone/web.py
# Description     : 
from __future__ import unicode_literals, print_function
from cyclone.http import get_request, HTTPHeaders
from cyclone.e import NotSupportMethod, ErrorStatusCode, MissArgument
from cyclone.utils import code_mess_map # 存的是http响应代码与信息的映射关系
from cyclone.escape import utf8
from cyclone.log import access_log, config_logging
import traceback

_ALL_METHOD = ('POST', 'GET', 'PUT', 'DELETE')

class RequestHandler():
    """主要类，在这里完成对用户的请求处理并返回"""
    def __init__(self, application, request):
        self.application = application
        self.request = request
        self._push_buffer = []
        self._finished = False
        self._headers = HTTPHeaders()
        if self.request.method not in _ALL_METHOD:
            raise NotSupportMethod

        self.init_data()
        self.init_headers()

    def init_data(self):
        """一些初始化工作都可以在这做"""
        pass

    def init_headers(self):
        self.set_headers({
            'Content-Type'  :       'text/plain; charset=utf-8',
            'Server'        :       'tuxpy server',
            })
        self.set_status(200)

    def ALL(self):
        pass

    def GET(self):
        raise NotSupportMethod

    def POST(self):
        raise NotSupportMethod

    def DELETE(self):
        raise NotSupportMethod

    def PUT(self):
        raise NotSupportMethod

    def push(self, _buffer):
        _buffer = utf8(_buffer)
        self._push_buffer.append(_buffer)

    def write(self, *args, **kwargs):
        """为了输出错误信息而设定的"""
        return self.push(*args, **kwargs)

    @property
    def is_finished(self):
        return self._finished

    def flush(self, _buffer = None):
        if self.is_finished:
            return

        _body = utf8(_buffer) or b''.join(self._push_buffer)

        self.set_header('Content-Length', len(_body))

        _headers = self._headers.get_response_headers_string(self.__response_first_line) # 把http头信息生成字符串
        self.request.connection.send_headers(_headers)
        self.request.connection.send_body(_body)

        self.log_print()

    def log_print(self):
        _log = "{method} {path} {response_first_line} {request_time}".format(
                method = self.request.method, path = self.request.path,
                response_first_line = self.__response_first_line,
                request_time = "%.2f%s" % (self.request.request_time * 1000, 'ms')
                )

        # 根据不同的http状态代码来输出不同的日志 
        if self._status_code < 400:
            access_log.info(_log)
        elif self._status_code < 500:
            access_log.warning(_log)
        else:
            access_log.error(_log)

    def on_finish(self):
        pass

    def finish(self):
        self.on_finish()
        if not self.is_finished:
            self.flush()
        
        self.request.connection.close()
        self._finished = True

    
    def set_header(self, name, value):
        self._headers[name] = value

    def set_headers(self, headers):
        if not isinstance(headers, dict):
            raise TypeError
        for _k, _v in headers.items():
            self.set_header(_k, _v)

    def set_status(self, status_code = 200, status_message = None):
        self.status_message = status_message # 可以自定义状态代码描述
        self._status_code = status_code

    def get_status(self):
        return self._status_code

    def raise_error(self, e):
        """当出现错误的时候会被调用"""
        _static_code = getattr(e, 'status_code', 500)
        _static_mess = getattr(e, 'status_mess', None)
        self.push_error(_static_code, _static_mess, e) # 调用错误处理函数

    def push_error(self, status_code = 500, status_mess = None, e = None):
        """处理http异常错误"""
        self.set_status(status_code, status_mess)
        self.send_error(traceback.format_exc())

    def send_error(self, exc):
        """把异常信息推送出去"""
        self._push_buffer = []
        if not self.settings.get('debug', False): # 只允许 在debug情况下输出错误
            return

        self.push(exc)
        self.push('\n' + self.__response_first_line)

    
    @property
    def __response_first_line(self):
        _message = self.status_message or code_mess_map.get(self._status_code) # 如果没有自定义状态代码描述的话，就根据标准来
        if not _message:
            raise ErrorStatusCode
        return "{version} {code} {message}".format(
                version = self.request.version, code = self.get_status(),
                message = _message)

    def get_query_arguments(self, param):
        return self.request.query_arguments.get(param, [])

    def get_body_arguments(self, param):
        return self.request.body_arguments.get(param, [])

    def get_query_argument(self, param, default = None):
        _args = self.get_query_arguments(param)
        return self.__get_one_argument(_args, param, default)

    def get_body_argument(self, param, default = None):
        _args = self.get_body_arguments(param)
        return self.__get_one_argument(_args, param, default)

    def get_argument(self, param, default = None):
        _args = self.request.all_arguments.get(param, [])
        return self.__get_one_argument(_args, param, default)

    def __get_one_argument(self, args, param, default = None):
        if (not args) and default: # 如果没有参数，但是指定了默认值，就返回默认的
            return default

        if not args:
            raise MissArgument
        return args[0]

    @property
    def settings(self):
        return self.application.settings

class Application(object):
    def __init__(self, handlers, settings = {}, log_settings = {}):
        """
        log_settings : {'level': log level(default: DEBUG'
                'datefmt': log date format(default: "%Y-%m-%d %H:%M:%S")}
        """
        self.handlers = handlers
        self.settings = settings
        config_logging(log_settings)

    def __call__(self, socket, address):
        request = get_request(socket) # 获取一个request，这里面有跟请求数据有关的东西

        """
        *******先假定handler就是/
        """
        handler = self._find_handler(request)(self, request)
        try:
            self.__exec_request(handler, request)
        except Exception as e:
            handler.raise_error(e) # 把异常传入，并分析，执行错误处理方法(push_error)
            traceback.print_exc()
        finally:
            handler.finish()

    def __exec_request(self, handler, request):
        handler.ALL() #  所有请求前都要先执行它
        _method_func = getattr(handler, request.method)
        _method_func()

    def _find_handler(self, request):
        """
        *******先假定handler就是/
        """
        return self.handlers[0][1]

