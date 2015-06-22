#!/usr/bin/env python
#coding:utf8
# Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-26 13:16:41
# Filename        : gale/web.py
# Description     : 
from __future__ import unicode_literals, print_function
try: 
    import Cookie # py2 
except ImportError:
    import http.cookies as Cookie

from gale.http import  HTTPHeaders
from gale.e import NotSupportMethod, ErrorStatusCode, MissArgument, HTTPError, LoginHandlerNotExists, LocalPathNotExist
from gale.utils import urlquote, urlunquote, ShareDict, made_uuid, get_mime_type, code_mess_map, format_timestamp # 存的是http响应代码与信息的映射关系
from gale.escape import utf8, param_decode, native_str
from gale.log import access_log, config_logging
from gale import template
from gale.session import FileSessionManager
import traceback
import time
from hashlib import md5
from functools import wraps
import os
import json
import glob
import gzip
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

try:
    import urlparse # py2
except ImportError:
    import urllib.parse as urlparse # py3

_ALL_METHOD = ('POST', 'GET', 'PUT', 'DELETE', 'HEAD')

class RequestHandler(object):
    """主要类，在这里完成对用户的请求处理并返回"""
    def __init__(self, application, request, kwargs = None):
        self.kwargs = kwargs or {}
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
        """设置response的headers信息"""
        self.set_headers({
            'Content-Type'  :       'text/plain; charset=utf-8',
            'Server'        :       'Gale Server',
            'Date'          :       format_timestamp(),
            })
        self.set_status(200)

    def set_default_headers(self):
        """可以在这里设置一些默认的headers信息(使用set_header[s])"""
        pass


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

    @property
    def login_url(self):
        return self.settings.get('login_url')

    @property
    def current_user(self):
        return self.get_current_user()

    def get_current_user(self):
        """如果需要实现用户验证，请在此完成，登录成功返回一个非False的值就行了，如果返回的是False，则表示验证失败，会被转到登录url上。"""
        return None

    def push(self, _buffer):
        if isinstance(_buffer, dict):
            _buffer = json.dumps(_buffer)
            self.set_header('Content-Type', 'application/json')

        _buffer = utf8(_buffer)
        self._push_buffer.append(_buffer)

    def is_supported_http1_1(self):
        return self.request.version == 'HTTP/1.1'

    @property
    def static_path(self):
        return self.settings.get('static_path')

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
            kwargs[_param_key] = native_str(kwargs[_param_key])

        _template_loader = self.application._template_cache.get(template_name)
        if not _template_loader:
            _template_loader = self.create_template_loader(self.get_template_path())
            if self.settings.get('debug') != True:
                self.application._template_cache[template_name] = _template_loader

        t = _template_loader.load(template_name)
        name_space = self.get_name_space()
        kwargs.update(name_space)
        kwargs['module'] = self._load_ui_module
        
        return t.generate(**kwargs)

    def create_template_loader(self, template_path):
        return template.Loader(template_path)

    def get_template_path(self):
        return self.settings.get('template_path', 'template')


    def get_name_space(self):
        """一些可以在模块中用的变量或方法"""
        name_space = {
                'client_ip' :   self.client_ip,
                'handler'   :   self,
                'request'   :   self.request, 
                'static_url'    :   self.get_static_url,
                '_tt_modules'   :   _UINameSpace(self),
                'current_user'  :   self.get_current_user(),
                }

        ext_name_space = self.get_ext_name_space()
        if not isinstance(ext_name_space, dict):
            raise TypeError
        name_space.update(ext_name_space)
        return name_space

    def get_ext_name_space(self):
        """可以在这里定义一些额外的namespce"""
        return {}

    def get_static_url(self, file_path):
        assert self.static_path, "static_url must had 'static_path' in app\'s settings"
        static_class = self.settings.get('static_class', StaticFileHandler)
        static_url = static_class.get_static_url(self.settings, file_path)
        return static_url


    @property
    def is_finished(self):
        return self._finished

    def process_buffer(self, _buffer):
        if self.settings.get('gzip', False):
            processor = GzipProcessor(self.request.headers)
            return processor.process(_buffer, self._headers, 
                    self.application._buffer_stringio)

        return _buffer

    def flush(self, _buffer = None):
        if self.request.connection.closed:
            return

        _buffer = _buffer or b''.join(self._push_buffer)
        self._push_buffer = []
        if self.is_finished:
            return

        self.set_header('Connection', self.request.is_keep_alive() and 'Keep-Alive' or 'Keep-Alive')

        if hasattr(self, '_new_cookie'):
            for cookie in self._new_cookie.values():
                self.add_header('Set-Cookie', cookie.OutputString())

        _body = self.process_buffer(_buffer)

        if self._status_code != 304: 
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
        """会在执行完finish时执行"""
        pass

    def finish(self):
        if self._finished:
            return
        if not self.is_finished:
            self.flush()

        if not self.request.is_keep_alive():
            self.request.connection.close()

        self._finished = True # 不管是不是keep alive，都需要把它设置成True，因为连接跟这个没关系，每一次有新的请求时，都会生成一个新的RequestHandler
        self.on_finish()

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
        name, value = native_str(name), native_str(value)
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
            pass
        self.push(self.__response_first_line)

    @property
    def _status_mess(self):
        return self.status_message or code_mess_map.get(self._status_code) # 如果没有自定义状态代码描述的话，就根据标准来
    
    @property
    def __response_first_line(self):
        _message = self._status_mess
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
        return self.__get_one_argument(_args, default)

    def get_body_argument(self, param, default = None):
        _args = self.get_body_arguments(param)
        return self.__get_one_argument(_args, default)

    def get_argument(self, param, default = None):
        _args = self.request.all_arguments.get(param, [])
        return self.__get_one_argument(_args, default)

    def get_arguments(self, param):
        return self.request.all_arguments.get(param, [])

    def get_files(self, name):
        return self.request.files.get(name, [])

    def get_file(self, name):
        return self.__get_one_argument(self.get_files(name))

    @property
    def session(self):
        _session = getattr(self, '_session', None)
        if _session != None:
            return _session

        from gale.session import Session

        _session_manager = getattr(self.application, 'session_manager', None)

        if not _session_manager:
            _session_manager = FileSessionManager(session_secret = 'galesessionsecret' ,
                        session_timeout = 86400 * 60) # 如果application中没有配置session_manager，则自动生成一个FileSessionManager，推荐想用session的请自己在application中指定 session_manager
            setattr(self.application, 'session_manager', _session_manager)

        _session = Session(_session_manager, self)

        setattr(self, '_session', _session)

        return _session

    def __get_one_argument(self, args, default = []):
        if (args == []) and (default != []): # 如果没有参数，但是指定了默认值，就返回默认的
            return default

        if args == []:
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


    def get_401_user_pwd(self):
        """在401验证时，获取用户输入的用户名和密码，返回tuple"""
        authorization = self.request.headers.get('Authorization')
        if not authorization:
            return None, None
        import base64
        user_pwd = base64.decodestring(authorization.split()[-1].strip())
        return user_pwd.split(':', 1)

class ErrorHandler(RequestHandler):
    def ALL(self):
        status_code = self.kwargs.get('status_code', 500)
        raise HTTPError(status_code)

class Application(object):
    _template_cache = {}
    _static_md5_cache = ShareDict()
    _buffer_stringio = StringIO()

    def __init__(self, handlers = [], vhost_handlers = [], settings = {}, log_settings = {},  ui_settings = {}):
        """
        log_settings : {'level': log level(default: DEBUG',
                'datefmt': log date format(default: "%Y-%m-%d %H:%M:%S"),
                'file': log save to file}
        ui_settings: {module_name: module(extends from UIModule)}
        """
        self.settings = settings
        self.ui_settings = ui_settings

        if settings.get('static_path'):
            static_class = settings.get('static_class', StaticFileHandler)
            for url_re in (r'%s(.*)' %
                (settings.get('static_prefix', r'/static/')),
                r'/(favicon\.ico)', r'/(robots\.txt)'):
                handlers.append((url_re, static_class))

        vhost_handlers = vhost_handlers or [('.*$', handlers)]
        self.vhost_handlers = []
        for _vhost_handler in vhost_handlers:
            self.add_handlers(*_vhost_handler)
        config_logging(log_settings)

    def __re_compile(self, re_string):
        """把正则规则都编译了，加快速度"""
        import re
        re_string = "%s%s%s" % ((not re_string.startswith('^')) and '^' or '', 
            re_string, (not re_string.endswith('$')) and '$' or '')  # 自动给url加上开头与结尾
        return re.compile(re_string)

    def add_handlers(self, re_host_string, host_handlers):
        _re_host_exists = False
        _compile_handlers = []
        for _a_url_item in host_handlers:
            assert len(_a_url_item) in (2, 3), "url args length must be 2 or 3 "

            if len(_a_url_item) == 2: # 如果没有传入handler参数，默认设定是空
                _a_url_item += ({}, )
            _re_string, _handler, _kwargs = _a_url_item
            _compile_handlers.append((self.__re_compile(_re_string), 
                _handler, _kwargs))

        for _re, _handlers in self.vhost_handlers:
            if _re.pattern == re_host_string:
                _handlers.extend(_compile_handlers)
                _re_host_exists = True
                break
        if not _re_host_exists:
            self.vhost_handlers.insert(-1, (self.__re_compile(re_host_string), _compile_handlers))
    
    def __call__(self, request, is_wsgi = False):
        if not request: # 如果无法获取一个request，则结束它，表示连接已经断开
            return

        request.real_ip = self.settings.get('real_ip', True) # 设定是否要获取真实ip地址

        handler, url_args, url_kwargs = self.__find_handler(request)
        url_args = map(urlunquote, url_args)
        try:
            self.__exec_request(handler, request, *url_args, **url_kwargs)
        except Exception as e:
            handler.raise_error(e) # 把异常传入，并分析，执行错误处理方法(push_error)
            if handler.get_status() >= 500: # 只有错误代码大于等于500才会打印出异常信息
                traceback.print_exc()
        finally:
            if (not is_wsgi) and (getattr(handler, 'is_long_poll', False) == False):
                handler.finish()

        return handler


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


        for url_re, url_handler, kwargs in self.handlers:
            _match = url_re.match(request_path)
            if _match: # 如果匹配上了，就执行下一步
                return url_handler(self, request, kwargs = kwargs), _match.groups(), _match.groupdict()

        default_handler = self.settings.get('default_handler')
        if default_handler: # 如果指定了默认处理，则调用，否则让ErrorHandler处理它，也就是会被当404处理
            return default_handler(self, request), (), {}
        else:
            return ErrorHandler(self, request, kwargs = {'status_code': 404}), (), {}


    def router(self, url, method = None, base_handler = None, host = '^.*$', kwargs = None, is_login = False, should_login = False):
        assert not (is_login and should_login) # 同时是登录类，又需要登录，这怎么可能呢
        base_handler =  self.__made_base_handler(host, url, base_handler) # 根据url来生成一个类

        method = method or 'GET'
        kwargs = kwargs or {}

        if is_login:
            self.settings['login_url'] = url

        if not isinstance(method, (tuple, list)):
            method = [method, ]

        for _method in method:
            if _method.upper() not in _ALL_METHOD:
                raise NotSupportMethod

        def method_func_wrap(method_func):
            @wraps(method_func)
            def wrap(self, *args, **kwargs):
                if should_login:
                    _func = authenticated(method_func)
                else:
                    _func = method_func

                return _func(self, *args, **kwargs)

            for _method in method:
                setattr(base_handler, _method.upper(), wrap)

            return wrap

        host_handler = (url, base_handler, kwargs)
        """ 这里需要处理把base添加到原来的vhost_handlers中去，如果已经有.*$了，并且有指定 host，就插入新的，如果没有host指定，则追进到旧的里去"""
        self.add_handlers(host, [host_handler, ])

        return method_func_wrap

    def __made_base_handler(self, host, url, base_handler = None):
        _base_handler = None
        url_compile = self.__re_compile(url)
        for re_host, vhost_handlers in self.vhost_handlers: # 先遍历下，看看有没有已经存在了的类
            if (re_host.match(host)):
                for re_url, _handler, _kwargs in vhost_handlers:
                    if re_url.pattern == url_compile.pattern:
                        _base_handler = _handler
                        vhost_handlers.remove((re_url, _handler, _kwargs))
                        break
                continue

        if _base_handler:
            return _base_handler

        _m = md5(utf8(url))
        _class_name = '_T%s_Handler' % (_m.hexdigest())
        return type(native_str(_class_name),
                (base_handler or RequestHandler, ), {})

    def run(self, host = '', port = 8080, **server_settings):
        http_server = HTTPServer(self, 
                host = host, port = port,
                **server_settings)
        http_server.run()


def authenticated(method):
    @wraps(method)
    def wrap(self, *args, **kwargs):
        if self.current_user:
            return method(self, *args, **kwargs)
        else:
            login_url = self.login_url
            if not login_url:
                raise LoginHandlerNotExists('Not found login handler or "login_url" not in application settings')
            if self.request.method in ('GET', 'HEAD'):
                callback_url = urlquote(self.request.uri)
                url_joiner = '?' in login_url and  '&'  or '?'
                self.redirect(login_url + url_joiner + 'callback=' + callback_url)
            else:
                raise HTTPError(403)

    return wrap

def auth_401(method):
    @wraps(method)
    def wrap(self, *args, **kwargs):
        if self.current_user:
            return method(self, *args, **kwargs)
        else:
            self.set_header('WWW-authenticate', "Basic realm='Please input'")
            raise HTTPError(401)

    return wrap

def long_poll(method):
    @wraps(method)
    def wrap(self, *args, **kwargs):
        self.is_long_poll = True
        return method(self, *args, **kwargs)

    return wrap

class UIModule(object):
    def __init__(self, handler):
        self.handler = handler
        self.request = handler.request

    def render(self):
        raise ImportError

    def render_string(self, template_name, *args, **kwargs):
        return self.handler.render_string(template_name, *args, **kwargs)



class StaticFileHandler(RequestHandler):
    absolute_path = None
    def HEAD(self, file_path):
        return self.GET(file_path, is_include_body = False)

    def GET(self, file_path, is_include_body = True):
        absolute_path = self.make_absolute_path(self.static_path,
                file_path)
        if not os.path.exists(absolute_path):
            raise HTTPError(404)

        self.absolute_path = absolute_path

        content_version = self.get_content_version(absolute_path)

        self.set_some_headers()
        self.set_etag_header(content_version)

        is_return_304 = self.should_return_304(content_version)

        if is_return_304:
            self.set_status(304)

        if is_include_body and (not is_return_304): # 如果是Flase，则表示是HEAD方法传过来的，这时候不需要发送文件
            for _data in self.get_content(absolute_path):
                self.push(_data)


    def should_return_304(self, content_version):
        """判断是否需要返回304,判断下request中的内容hash值与计算出来的是否一样就行了"""
        return self.get_request_version() == content_version

    def get_request_version(self):
        """获取request中的内容hash值"""
        version = self.request.headers.get('If-None-Match', '')
        return version

    @classmethod
    def get_content(cls, absolute_path):
        with open(absolute_path, 'rb') as fd:
            while True:
                chunk_size = 1024 * 8
                chunk = fd.read(chunk_size)
                if chunk:
                    yield chunk
                else:
                    return

    def set_some_headers(self):
        self.set_header('Content-Type', get_mime_type(self.absolute_path))
        self.set_expire_header()

    def set_expire_header(self):
        """这是在设置跟过期有关的http头"""
        expire_sec = 86400 * 365 * 10
        if self.is_supported_http1_1():
            self.set_header('Cache-Control', 'max-age=%s' % (expire_sec))
        else:
            self.set_header('Expires', format_timestamp(time.time() + expire_sec))

    def set_etag_header(self, etag = None):
        if not self.is_supported_http1_1(): # 如果不是http 1.1则是不支持的（比如 1.0)
            return 

        etag = etag or self.get_content_version(self.absolute_path)
        self.set_header('Etag', etag)

    def get_content_version(self, absolute_path):
        _cache_version = self.get_cache_version(absolute_path)
        if _cache_version:
            return _cache_version

        md5er = md5()
        for _chunk in self.get_content(absolute_path):
            md5er.update(_chunk)
        _md5 = md5er.hexdigest() 
        self._md5_cache[absolute_path] = {'md5': _md5,
                'mtime': self.file_stat().st_mtime}

        return _md5

    def get_cache_version(self, absolute_path):
        _cache = self._md5_cache.get(absolute_path)
        if not _cache:
            return None

        if self.file_stat().st_mtime != _cache['mtime']: # 如果已经修改过了，则表示已经更新了，则需要重新计算hash值
            del self._md5_cache[absolute_path]
            return None

        return _cache['md5']

    @property
    def _md5_cache(self):
        return self.application._static_md5_cache

    @classmethod
    def make_absolute_path(cls, root, path):
        return os.path.join(root, path)

    @classmethod
    def get_static_url(cls, settings, file_path):
        static_path = settings.get('static_path')
        if static_path.startswith('http'): # 让static同时支持在线资源
            return urlparse.urljoin(static_path, file_path)

        static_prefix = settings.get('static_prefix', '/static/')
        return urlparse.urljoin(static_prefix, file_path)

    def file_stat(self):
        return os.stat(self.absolute_path)


class GzipProcessor(object):
    COMPRESSION_LEVEL = 7
    ALLOW_CONTENT_TYPE = ('text/*', '*javascript', '*json*', '*xml*', 
            'image/*')
    MIN_LENGTH = 100

    def __init__(self, request_headers):
        self.should_gzip = 'gzip' in request_headers.get('Accept-Encoding', '')

    def process(self, _buffer, response_headers, _buffer_stringio):
        if len(_buffer) < self.MIN_LENGTH:
            self.should_gzip = False

        if not self.should_gzip:
            return _buffer

        is_compesssion_type = False
        content_type = response_headers.get('Content-Type', '').split(';')[0]
        if not content_type: # 如果没有指定 Content-Type则返回 
            return _buffer
        for _type in self.ALLOW_CONTENT_TYPE:
            if glob.fnmatch.fnmatch(content_type, _type):
                is_compesssion_type = True
                break

        if not is_compesssion_type:  # 如果不是压缩对象，则也返回
            return _buffer


        _gzip_file = gzip.GzipFile(mode = 'wb', fileobj = _buffer_stringio, compresslevel = self.COMPRESSION_LEVEL)
        _gzip_file.write(_buffer)
        _gzip_file.close()
        compression_data  = _buffer_stringio.getvalue()
        _buffer_stringio.seek(0)

        response_headers['Content-Encoding']  = 'gzip'

        return compression_data

class _UINameSpace(object):
    def __init__(self, handler):
        self.handler = handler
    
    def __getattr__(self, module):
        _module = self.handler.ui_settings.get(module)
        _module_instance = _module(self.handler)
        return _module_instance.render

from gale.server import HTTPServer
HANDLER_LIST = []

def router(*args, **kwargs):
    def wraps(method_func):
        HANDLER_LIST.append((method_func, args, kwargs))

    return wraps

def app_run(app_path = None, settings = {}, log_settings={}, server_settings = {}, host = '', port = 8080):
    """在这里的app_path决定着默认template和static_path，默认是执行脚本程序时的工作目录"""
    settings.setdefault('debug', True)
    settings.setdefault('static_path', os.path.join(app_path and os.path.dirname(os.path.abspath(app_path)) or os.getcwd(), 'static'))
    settings.setdefault('template_path', os.path.join(app_path and os.path.dirname(os.path.abspath(app_path)) or os.getcwd(), 'template'))

    app = Application(settings = settings, 
            log_settings = log_settings)
    for handler_func, args, kwargs in HANDLER_LIST:
        app.router(*args, **kwargs)(handler_func)

    http_server = HTTPServer(app, host = host, port = port, **server_settings)
    http_server.run(processes = 0)

