#!/usr/bin/env python
#coding:utf8
# Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-26 13:16:41
# Filename        : cyclone/web.py
# Description     : 
from __future__ import unicode_literals, print_function
from cyclone.http import  HTTPHeaders
from cyclone.e import NotSupportMethod, ErrorStatusCode, MissArgument, HTTPError
from cyclone.utils import code_mess_map, format_timestamp # 存的是http响应代码与信息的映射关系
from cyclone.escape import utf8, param_decode
from cyclone.log import access_log, config_logging
from cyclone.template import Env
import Cookie
import traceback
import time
from hashlib import md5
from functools import wraps

try:
    import urlparse # py2
except ImportError:
    import urllib.parse as urlparse # py3

_ALL_METHOD = ('POST', 'GET', 'PUT', 'DELETE', 'HEAD')

class RequestHandler(object):
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
            'Date'          :       format_timestamp(),
            'Connection'    :       self.request.is_keep_alive() and 'Keep-Alive' or 'Keep-Alive',
            })
        self.set_status(200)

    def ALL(self, *args, **kwargs):
        pass

    def HEAD(self, *args, **kwargs):
        raise NotSupportMethod

    def GET(self, *args, **kwargs):
        raise NotSupportMethod

    def POST(self, *args, **kwargs):
        raise NotSupportMethod

    def DELETE(self, *args, **kwargs):
        raise NotSupportMethod

    def PUT(self, *args, **kwargs):
        raise NotSupportMethod

    def push(self, _buffer):
        _buffer = utf8(_buffer)
        self._push_buffer.append(_buffer)

    def redirect(self, url, temp = True, status_code = None):
        if not status_code:
            status_code = temp and 302 or 301 # 如果没有指定 status_code， 则根据是否是临时重定向来决定code

        if bool(self._push_buffer):
            raise Exception("Can't redirect after push")
        assert isinstance(status_code ,int) and (300 <= status_code <= 399)
        self.set_status(status_code)

        self.set_header('Location', urlparse.urljoin(utf8(self.request.uri), utf8(url)))

    def render(self, template_name, **kwargs):
        if self.is_finished:
            return False
        render_string = self.render_string(template_name, **kwargs)

        self.set_header('Content-Type', 'text/html;charset=UTF-8')
        self.push(render_string)


    def render_string(self, template_name, **kwargs):
        for _param_key in kwargs:
            kwargs[_param_key] = param_decode(kwargs[_param_key])

        _template = self.application._template_cache.get(template_name)
        if not _template:
            _template = self.template_env.get_template(template_name)
            self.application._template_cache[template_name] = _template

        name_space = self.get_name_space()
        kwargs.update(name_space)
        kwargs['module'] = self._load_ui_module

        return _template.render(**kwargs)

    def get_name_space(self):
        """一些可以在模块中用的变量或方法"""
        name_space = {
                'client_ip' :   self.client_ip,
                'handler'   :   self,
                'request'   :   self.request, 
                }

        return name_space

    @property
    def template_env(self):
        return self.application.template_env


    @property
    def is_finished(self):
        return self._finished

    def flush(self, _buffer = None):
        if self.is_finished:
            return

        if hasattr(self, '_new_cookie'):
            for cookie in self._new_cookie.values():
                self.add_header('Set-Cookie', cookie.OutputString())

        _body = utf8(_buffer) or b''.join(self._push_buffer)

        self.set_header('Content-Length', len(_body))

        _headers = self._headers.get_response_headers_string(self.__response_first_line) # 把http头信息生成字符串
        self.request.connection.send_headers(_headers)

        if self.request.method != 'HEAD': # 如果是HEAD请求的话则不返回主体内容
            self.request.connection.send_body(_body)

        self.log_print()

    def log_print(self):
        _log = "{method} {path} {response_first_line} {client_ip} {request_time}".format(
                method = self.request.method, path = self.request.path,
                response_first_line = self.__response_first_line,
                client_ip = self.client_ip,
                request_time = "%.2f%s" % (self.request.request_time * 1000, 'ms')
                )

        # 根据不同的http状态代码来输出不同的日志 
        if self._status_code < 400:
            access_log.info(_log)
        elif self._status_code < 500:
            access_log.warning(_log)
        else:
            access_log.error(_log)

    @property
    def client_ip(self):
        return self.request.client_ip

    def on_finish(self):
        pass

    def finish(self):
        self.on_finish()
        if not self.is_finished:
            self.flush()

        if not self.request.is_keep_alive():
            self.request.connection.close()
            self._finished = True


    def set_header(self, name, value):
        value = utf8(value)
        self._headers[name] = value

    def add_header(self, name, value):
        value = utf8(value)
        self._headers.add(name, value)

    def set_headers(self, headers):
        if not isinstance(headers, dict):
            raise TypeError
        for _k, _v in headers.items():
            self.set_header(_k, _v)

    @property
    def cookies(self):
        """本次请求中所有的cookies"""
        return self.request.cookies

    def set_cookie(self, name, value, domain=None, expires=None, path = '/', expires_day = None, **kwargs):
        self._new_cookie = getattr(self, '_new_cookie', Cookie.SimpleCookie())
        self._new_cookie.pop(name, None) # 如果已经存在了，则删除它

        self._new_cookie[name] = value
        morsel = self._new_cookie[name]
        if domain:
            morsel['domain'] = domain

        if path:
            morsel['path'] = path

        if expires_day and (not expires):
            expires = expires_day * 60 * 60 * 24

        if expires:
            morsel['expires'] = format_timestamp(time.time() + expires)

        for k, v in kwargs.items():
            if k == 'max_age':
                k = 'max-age'
            morsel[k] = v

    def clear_cookie(self, name, path = '/', domain = None):
        self.set_cookie(name, value = '', 
                path = path, domain = domain, expires = -100)

    def clear_all_cookies(self, path = '/', domain = None):
        for _cookie_name in self.cookies:
            self.clear_cookie(name, path = path, domain = domain)

    def get_cookie(self, cookie_name, default = None):
        return self.cookies.get(cookie_name, default)

    def set_status(self, status_code = 200, status_message = None):
        self.status_message = status_message # 可以自定义状态代码描述
        self._status_code = status_code

    def get_status(self):
        return self._status_code

    def raise_error(self, e):
        """当出现错误的时候会被调用"""
        _status_code = getattr(e, 'status_code', 500)
        _status_mess = getattr(e, 'status_mess', None)
        self.set_status(_status_code, _status_mess)
        self.push_error() # 调用错误处理函数

    def push_error(self):
        """处理http异常错误"""
        self.send_error(traceback.format_exc())

    def send_error(self, exc):
        """把异常信息推送出去"""
        exc = utf8(exc)
        self._push_buffer = []
        if not self.settings.get('debug', False): # 只允许 在debug情况下输出错误
            return

        if self.get_status() >= 500:
            self.push(exc + b'\n')
        else:
            traceback.sys.exc_clear()
        self.push(self.__response_first_line)

    
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

    @property
    def ui_settings(self):
        return self.application.ui_settings

    def _load_ui_module(self, module_name, *args, **kwargs):
        _module = self.ui_settings.get(module_name)
        assert issubclass(_module, UIModule), 'module must extend from UIModule'
        _module_instance = _module(self)
        return _module_instance.render(*args, **kwargs)

class ErrorHandler(RequestHandler):
    def ALL(self, status_code):
        raise HTTPError(status_code)


class Application(object):
    _template_cache = {}

    def __init__(self, handlers = [], vhost_handlers = [], settings = {}, log_settings = {}, template_settings = {}, ui_settings = {}):
        """
        log_settings : {'level': log level(default: DEBUG'
                'datefmt': log date format(default: "%Y-%m-%d %H:%M:%S")}
        template_settings: {'template_path': 'xxx'...} like jinja env
        ui_settings: {module_name: module(extends from UIModule)}
        """
        vhost_handlers = vhost_handlers or [('.*$', handlers)]
        self.vhost_handlers = []
        for _vhost_handler in vhost_handlers:
            self.add_handlers(*_vhost_handler)
        self.settings = settings
        config_logging(log_settings)
        self.template_env = Env(template_settings)
        self.ui_settings = ui_settings

    def __re_compile(self, re_string):
        """把正则规则都编译了，加快速度"""
        import re
        re_string = "%s%s%s" % ((not re_string.startswith('^')) and '^' or '', 
            re_string, (not re_string.endswith('$')) and '$' or '')  # 自动给url加上开头与结尾
        return re.compile(re_string)

    def add_handlers(self, re_host_string, host_handlers):
        _re_host_exists = False
        _compile_handlers = []
        for _re_string, _handler in host_handlers:
            _compile_handlers.append((self.__re_compile(_re_string), 
                _handler))

        for _re, _handlers in self.vhost_handlers:
            if _re.pattern == re_host_string:
                _handlers.extend(_compile_handlers)
                _re_host_exists = True
                break
        if not _re_host_exists:
            self.vhost_handlers.insert(-1, (self.__re_compile(re_host_string), _compile_handlers))

    def __call__(self, request):
        if not request: # 如果无法获取一个request，则结束它，表示连接已经断开
            return

        request.real_ip = self.settings.get('real_ip', True) # 设定是否要获取真实ip地址

        handler, args, kwargs = self.__find_handler(request)
        try:
            self.__exec_request(handler, request, *args, **kwargs)
        except Exception as e:
            handler.raise_error(e) # 把异常传入，并分析，执行错误处理方法(push_error)
            if handler.get_status() >= 500: # 只有错误代码大于等于500才会打印出异常信息
                traceback.print_exc()
        finally:
            handler.finish()

    def __exec_request(self, handler, request, *args, **kwargs):
        handler.ALL(*args, **kwargs) #  所有请求前都要先执行它
        _method_func = getattr(handler, request.method) 
        _method_func(*args, **kwargs)

    def __find_handler(self, request):
        """根据url来决定将任务交由哪个handler去处理, 会返回handler，还有url参数"""
        request_path = request.path
        request_host = request.host

        for vhost_re, handlers in self.vhost_handlers: # 如果启用了虚拟主机，则做一下host字段的匹配
            if vhost_re.match(request_host):
                self.handlers = handlers
                break

        for url_re, url_handler in self.handlers:
            _match = url_re.match(request_path)
            if _match: # 如果匹配上了，就执行下一步
                return url_handler(self, request), _match.groups(), _match.groupdict()

        default_handler = self.settings.get('default_handler')
        if default_handler: # 如果指定了默认处理，则调用，否则让ErrorHandler处理它，也就是会被当404处理
            return default_handler(self, request), (), {}
        else:
            return ErrorHandler(self, request), (), {'status_code': 404}

class RouterApplication(Application):
    def router(self, url, method = None, base_handler = None, host = '.*$'):
        base_handler = base_handler or self.__made_base_handler(url) # 根据url来生成一个类

        method = method or 'GET'
        if not isinstance(method, (tuple, list)):
            method = [method, ]

        for _method in method:
            if _method not in _ALL_METHOD:
                raise NotSupportMethod

        def method_func_wrap(method_func):
            @wraps(method_func)
            def wrap(self, *args, **kwargs):
                return method_func(self, *args, **kwargs)

            for _method in method:
                setattr(base_handler, _method.upper(), wrap)

            return wraps

        host_handler = (url, base_handler)
        """ 这里需要处理把base添加到原来的vhost_handlers中去，如果已经有.*$了，并且有指定 host，就插入新的，如果没有host指定，则追进到旧的里去"""
        self.add_handlers(host or '.*$', [host_handler, ])

        return method_func_wrap

    def __made_base_handler(self, url):
        _m = md5(url)
        _class_name = '_T%s_Handler' % (_m.hexdigest())
        return type(utf8(_class_name),
                (RequestHandler, ), {})

class UIModule(object):
    def __init__(self, handler):
        self.handler = handler
        self.request = handler.request

    def render(self):
        raise ImportError

    def render_string(self, template_name, *args, **kwargs):
        return self.handler.render_string(template_name, *args, **kwargs)

