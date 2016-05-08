#!/usr/bin/env python
#coding:utf8 # Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-26 13:16:41
# Filename        : gale/web.py
# Description     : 
from __future__ import unicode_literals, print_function
try: 
    import Cookie # py2 
except ImportError:
    import http.cookies as Cookie

from gale import template, cache
from gale.http import  HTTPHeaders
from gale.e import HasFinished, NotSupportMethod, ErrorStatusCode, MissArgument, HTTPError, LoginHandlerNotExists, LocalPathNotExist, CookieError, CacheError
from gale.utils import  parse_request_range, single_pattern, is_string, urlsplit, urlquote, urlunquote, ShareDict, made_uuid, get_mime_type, format_timestamp, code_mess_map # 存的是http响应代码与信息的映射关系
from gale.escape import utf8, param_decode, native_str, to_unicode
from gale.log import (access_log, config_logging, generate_request_log)
from gale.ipc import IPCDict
from gale.session import FileSessionManager
from gale.restapi import RestApi

import traceback
import time
from functools import wraps
import hashlib
import hmac 
import os 
import json
import glob
import gzip
import re
import base64
import gevent
import types

try:
    from cStringIO import StringIO as s_io
except ImportError:
    try:
        from StringIO import StringIO as s_io
    except ImportError:  #  py3
        from io import BytesIO as s_io

try:
    import urlparse # py2
except ImportError:
    import urllib.parse as urlparse # py3

_ALL_METHOD = ('POST', 'GET', 'PUT', 'DELETE', 'HEAD')
re_signed_cookie = re.compile(r'^\|\d+')

BUFFER_SIZE = 4096 * 10

def auth_401(method):
    @wraps(method)
    def wrap(self, *args, **kwargs):
        if self.current_user:
            return method(self, *args, **kwargs)
        else:
            self.set_header('WWW-Authenticate', "Basic realm='Please input'")
            raise HTTPError(401)

    return wrap


class ResponseBody(object):
    """This is RequestHandler.push syntactic sugar"""
    def __set__(self, handler, value):
        self.handler._push_buffer = []
        self.handler.push(value)

    def __get__(self, handler, handler_class):
        self.handler = handler
        return self

    def __add__(self, value):
        self.handler.push(value)

class ResponseBodyBuffer(list):
    def __add__(self, _buffer):
        print(_buffer)

class RequestHandler(object):
    """主要类，在这里完成对用户的请求处理并返回"""
    def __init__(self, application, request, kwargs = None):
        self.kwargs = kwargs or {}
        self.application = application
        self.request = request
        self.cache_page = False
        self.response_body = None
        self._finished = False
        self._headers = HTTPHeaders()
        self._buffer_md5 = hashlib.md5()
        self.query = ParamsObject(self.request.query_arguments)
        self._body = BodyParamsResponseObject(self.request.body_arguments)
        self.__been_writen_headers = False
        self.__is_sending_file = True # 表示正在发送文件， flush_body的方式会改变
        self.request.connection.on_close_callback = self.on_connect_close

        if self.request.method not in _ALL_METHOD:
            raise NotSupportMethod

        self.init_data()
        self.init_headers()

    @property
    def body(self):
        return self._body

    @body.setter
    def body(self, _buffer):
        self._body.set_buffer(_buffer)

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

    @property
    def allow_methods(self):
        return [ method for method in _ALL_METHOD if hasattr(self, method)]

    def set_default_headers(self):
        """可以在这里设置一些默认的headers信息(使用set_header[s])"""
        pass

    def ALL(self, *args, **kwargs):
        pass

    """
    # 当http request到来时，会自动调用Handler下的对应方法
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
    """

    @property
    def server_settings(self):
        return self.application.server_settings

    @property
    def login_url(self):
        return self.settings.get('login_url')

    @property
    def current_user(self):
        return self.get_current_user()

    def _generate_abspath(self, *p):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                *p)

    def get_current_user(self):
        """如果需要实现用户验证，请在此完成，登录成功返回一个非False的值就行了，如果返回的是False，则表示验证失败，会被转到登录url上。"""
        return None

    def push(self, _buffer):
        if self.is_finished:
            raise HasFinished('can\' push finished after')

        if isinstance(_buffer, dict):
            _buffer = json.dumps(_buffer)
            self.set_header('Content-Type', 'application/json')

        _buffer = utf8(_buffer)
        if self.settings.get('dynamic_304', True):
            self._buffer_md5.update(_buffer)
        self.body + _buffer

    def is_supported_http1_1(self):
        return self.request.version == 'HTTP/1.1'

    @property
    def static_path(self):
        return self.settings.get('static_path')

    def redirect(self, url, temp = True, status_code = None):
        if not status_code:
            status_code = temp and 302 or 301 # 如果没有指定 status_code， 则根据是否是临时重定向来决定code

        if not self.body.empty():
            raise Exception("Can't redirect after push")
        assert isinstance(status_code ,int) and (300 <= status_code <= 399)
        self.set_status(status_code)

        self.set_header('Location', urlparse.urljoin(utf8(self.request.uri), utf8(url)))

    def render(self, template_name, **kwargs):
        if self.is_finished:
            return False
        html = to_unicode(self.render_string(template_name, **kwargs))

        # 自动加载js
        load_js_list = self.__get_load_list('js')
        if load_js_list:
            offset = html.rfind('</body>')
            js_html = '\n'.join(['<script src="{js_path}"></script>'.format(js_path = to_unicode(js_path)) for js_path in load_js_list])

            html = html[:offset] + js_html + '\n' + html[offset:]

        # 自动加载css
        load_css_list = self.__get_load_list('css')
        if load_css_list:
            offset = html.rfind('</head>')
            css_html = '\n'.join(['<link rel="stylesheet" href="{css_path}" />'.format(css_path = to_unicode(css_path)) for css_path in load_css_list])
            html = html[:offset] + css_html + '\n' + html[offset:]

        self.set_header('Content-Type', 'text/html;charset=UTF-8')
        self.push(html)

    def __get_load_list(self, _type):
        assert _type in ('js', 'css')

        _list = []
        load_list = getattr(self, 'load_' + _type)()
        if not load_list:
            return []

        load_list = isinstance(load_list, (list, tuple)) and load_list or [load_list]

        for _item in load_list:
            _abs_path = self.get_static_url(_item, is_abs = True)
            if os.path.exists(_abs_path) == False:
                raise OSError('%s not exist' % (_abs_path, ))

            if os.path.isdir(_abs_path):
                _list.extend([_url for _url in self.get_static_urls(_item) \
                        if _url.endswith('.' + _type)]) # 当css时，过滤掉非css的，js时，过滤掉非js的
            else:
                _list.append(self.get_static_url(_item))

        return _list

    def load_js(self):
        return []

    def load_css(self):
        return []

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

    def string_render(self, string, **kwargs):
        _template_loader = self.create_template_loader()
        name_space = self.get_name_space()
        kwargs.update(name_space)
        t = _template_loader.load(string)
        return t.generate(**kwargs)

    def send_file(self, attr_path, attr_name = None, charset = 'utf-8', speed = None, is_attr = True):
        """speed: 下载速度, 单位是字节B"""
        if not self.body.empty():
            raise Exception("Can't redirect after push")

        if not os.path.isfile(attr_path):
            raise OSError('file: %s  not found' % (attr_path, ))


        attr_name = attr_name or os.path.basename(attr_path)
        self.set_header('Content-Type', get_mime_type(attr_path))
        if is_attr:
            self.set_header('Content-Disposition', 
                    native_str('attachment;filename="%s"') % (native_str(attr_name), ))
            self.set_header('Accept-Ranges', 'bytes')

        self.__is_sending_file = True

        sleep_secs = speed and (1.0 / (1.0 * speed / BUFFER_SIZE)) or None

        file_size = os.stat(attr_path).st_size
        read_range = self.request.get_header('Range', None)
        start, _ = parse_request_range(read_range) # 由于是断点续传，只考虑start
        if start > 0:
            self.set_header('Content-Range', 
                    'bytes %s-%s/%s' % (start, file_size - 1, file_size))
            self.set_status(206)
        self.set_header('Content-Length', file_size - start)
        
        self.__send_file(attr_path, sleep_secs, start = start)

        self.finish()

    def __send_file(self, attr_path, sleep_secs = None, start = 0):
        with open(attr_path, 'rb') as fd:
            fd.seek(start)
            while not self.request.connection.closed:
                _content = fd.read(BUFFER_SIZE)
                if not _content:
                    break;
                self.push(_content)
                self.flush()
                if sleep_secs:
                    gevent.sleep(sleep_secs)

            self.body.flush_buffer()

    def create_template_loader(self, template_path = None):
        return template_path and template.Loader(template_path) or template.StringLoader()

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
                'current_user'  :   self.get_current_user,
                }

        ext_name_space = self.get_ext_name_space()
        if not isinstance(ext_name_space, dict):
            raise TypeError
        name_space.update(ext_name_space)
        return name_space

    def get_ext_name_space(self):
        """可以在这里定义一些额外的namespce"""
        return {}

    def get_static_url(self, file_path, is_abs = False):
        assert self.static_path, "static_url must had 'static_path' in app\'s settings"
        static_class = self.settings.get('static_class', StaticFileHandler)
        if is_abs:
            return static_class.make_absolute_path(self.static_path, file_path)
        static_url = static_class.get_static_url(self.settings, file_path)
        return static_url

    def get_static_urls(self, path):
        """获取某一个目录下的所有静态资源"""
        assert self.static_path, "get_static_urls must had 'static_path' in app\'s settings"
        abs_path = self.get_static_url(path, is_abs = True)
        if not os.path.isdir(abs_path):
            return [abs_path]

        urls = []
        for dirname, _, _files  in os.walk(abs_path):
            for _file in _files:
                url = os.path.join(dirname, _file)[len(self.static_path) + 1: ]
                urls.append(self.get_static_url(url))

        return urls

    @property
    def is_finished(self):
        return self._finished

    def process_buffer(self, _buffer):
        if self.settings.get('gzip', False):
            processor = GzipProcessor(self.request.headers)
            return processor.process(_buffer, self._headers, 
                    self.application._buffer_stringio)

        return _buffer

    def should_return_304(self, buffer_md5):
        if self.get_status() not in (200, 304):
            return False

        if self.request.method != 'GET':
            return False

        dynamic_304 = self.settings.get('dynamic_304', True)
        if dynamic_304 == False or self.request.get_header('Cache-Control') == 'no-cache':
            return False

        request_version = self.request.get_header('If-None-Match', '')
        if not request_version:
            return False

        return request_version == buffer_md5

    def _flush_body(self, response_body):
        connection = self.request.connection
        if self.__is_sending_file:
            if response_body:
                connection.send_body(response_body)
            else:
                connection.send_finish_tag()
            return

        _buffer_md5 = self._buffer_md5.hexdigest()
        self.set_header('Etag', _buffer_md5)

        is_return_304 = self._status_code == 304 or self.should_return_304(_buffer_md5)
        if is_return_304:
            self.set_status(304)

        if is_return_304 != True and self.request.method != 'HEAD': # 如果是HEAD请求的话则不返回主体内容
            connection.send_body(response_body)
            connection.send_finish_tag()

    def flush(self, _buffer = None):
        self.before_flush()
        if self.is_finished:
            return

        if self.request.connection.closed:
            return

        _buffer = _buffer or self.body.to_bytes()
        _response_body = self.process_buffer(_buffer)

        if self.__been_writen_headers == False:
            self.__been_writen_headers = True
            self.set_header('Connection', self.request.is_keep_alive() and 'Keep-Alive' or 'Close')
            self.set_default_header('Content-Length', len(_response_body))
            if hasattr(self, '_new_cookie'):
                for cookie in self._new_cookie.values():
                    self.add_header('Set-Cookie', cookie.OutputString())
            _headers = self._headers.get_response_headers_string(self.response_first_line) # 把http头信息生成字符串
            self.request.connection.send_headers(_headers)

        self._flush_body(_response_body)
        self.body.flush_buffer()

        if self.cache_page and self._status_code in (200, 304):
            self.response_body = _buffer
        else:
            self.response_body = None

        del _buffer

    def log_print(self):
        _log = generate_request_log(self)

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

    def on_referrer_error(self):
        raise HTTPError(403)

    def on_finish(self):
        """会在执行完finish时执行"""
        pass

    def before_flush(self):
        """在刷新前做点事"""
        pass

    def finish(self, chunk = None):
        if self._finished:
            return
        if not self.is_finished:
            self.flush(chunk)

        if not self.request.is_keep_alive():
            self.request.connection.close()

        self._finished = True # 不管是不是keep alive，都需要把它设置成True，因为连接跟这个没关系，每一次有新的请求时，都会生成一个新的RequestHandler
        self.log_print()
        self.on_finish()

    def set_default_header(self, name, value):
        self._headers.set_default_header(name, value)

    def get_been_set_header(self, name, default = ''):
        try:
            return self._headers[name]
        except KeyError:
            return default

    def set_header(self, name, value):
        if value == None:
            return
        self._headers[name] = value

    def clear_headers(self):
        self._headers.clear()

    def add_header(self, name, value):
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
        value = self.cookies.get(cookie_name, default)
        if value and value[0] == '\"' and value[-1] == '\"':
            return value[1: -1]
        else:
            return value

    def get_signed_cookie(self, cookie_name, default = None):
        secret = self.settings.get('cookie_secret', None)
        if not secret:
            raise CookieError("use signed cookie app\'s settings must has 'cookie_secret'")
        value = self.get_cookie(cookie_name)
        if value == None:
            return default

        if (not re_signed_cookie.match(value)) and self.cookie_support_tornado == False:
            return None

        if self.cookie_support_tornado:
            return decode_signed_cookie_tornado(secret, cookie_name, value)
        else:
            return decode_signed_cookie(secret, cookie_name, value)

    def set_signed_cookie(self, name, value, *args, **kwargs):
        secret = self.settings.get('cookie_secret', None)
        if not secret:
            raise CookieError("use signed cookie app\'s settings must has 'cookie_secret'")

        signed_value = encode_signed_cookie(secret, name, value)
        self.set_cookie(name, signed_value, *args, **kwargs)

    @property
    def cookie_support_tornado(self):
        return bool(self.settings.get('cookie_support_tornado', False))

    def set_status(self, status_code = 200, status_message = None):
        self.status_message = status_message # 可以自定义状态代码描述
        self._status_code = status_code

    def get_status(self):
        return self._status_code

    def process_raise_error(self, e):
        """当出现错误的时候会被调用"""
        _status_code = getattr(e, 'status_code', 500)
        _status_mess = getattr(e, 'status_mess', None)
        self.set_status(_status_code, _status_mess)
        self.push_error() # 调用错误处理函数

    def push_error(self):
        """处理http异常错误"""
        if self.is_finished:
            return
        self.send_error(traceback.format_exc())

    def raise_error(self, status_code = 500, status_msg = None):
        raise HTTPError(status_code, status_msg)

    def send_error(self, exc):
        """把异常信息推送出去"""
        exc = utf8(exc)
        self.body.flush_buffer()
        self.push(self.response_first_line)
        if not self.settings.get('debug', False): # 只允许 在debug情况下输出错误
            return

        if self.get_status() >= 500:
            self.push(exc + b'\n')
        else:
            pass

    @property
    def _status_mess(self):
        return self.status_message or code_mess_map.get(self._status_code) # 如果没有自定义状态代码描述的话，就根据标准来
    
    @property
    def response_first_line(self):
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

    def get_cache_manager(self, on = None):
        s_cache_manager = self.settings.get('cache_manager', None)
        if not s_cache_manager:
            raise CacheError('use cache , app\'s settings must has cache_manager')
        if on == None: # 表示获取默认的cache manager
            if isinstance(s_cache_manager, (tuple, list)): # 如果有指定多个，则默认是以第一个为cache_manager
                s_cache_manager = s_cache_manager[0]

            return s_cache_manager
        else:
            on = utf8(on)
            _cache_manager = getattr(self.application, on + '_cache_manager', None) # 这主要是用来减少判断的，对不同的cache_manager只需要做一个判断，就可以找出哪个on，对应的是哪个列表中的元素了
            if _cache_manager:
                return _cache_manager

            if not isinstance(s_cache_manager, (tuple, list)):
                raise CookieError("use 'on' arg, cache_manager setting must be tuple or list")
            for _cm in s_cache_manager:
                if _cm.__name__ == on:
                    setattr(self.application, on + '_cache_manager', _cm)
                    return _cm

            raise CookieError('Not Found %s cache_manager' % (on, ))

    def get_401_user_pwd(self):
        """在401验证时，获取用户输入的用户名和密码，返回tuple"""
        authorization = self.request.headers.get('Authorization')
        if not authorization:
            return None, None
        import base64
        user_pwd = base64.decodestring(authorization.split()[-1].strip())
        return user_pwd.split(':', 1)

    def on_connect_close(self):
        pass

class _FileItem(object):
    def __init__(self, root, relative_path):
        self.root = root
        self.relative_path = relative_path or '/'

    @property
    def pretty_name(self):
        basename = self.relative_path
        if self.isdir and self.relative_path[-1] != '/':
            return basename + '/'
        else:
            return basename

    @property
    def showpath(self):
        return os.path.join(self.root, self.relative_path)

    @property
    def dirname(self):
        return os.path.dirname(self.abspath)

    @property
    def isfile(self):
        return os.path.isfile(self.abspath)

    @property
    def isdir(self):
        return os.path.isdir(self.abspath)

    @property
    def name(self):
        return os.path.basename(self.abspath)

    @property
    def ishidden(self):
        basename = os.path.basename(self.abspath)
        return basename[0] == '.'

    def __repr__(self):
        return self.abspath

    @property
    def raw_size(self):
        return self.stat.st_size

    @property
    def pretty_size(self):
        raw_size = self.raw_size
        pretty_size = raw_size

        unit = 'B'
        for _unit in ['KB', 'MB', 'GB']:
            pretty_size /= 1024.0
            if pretty_size <= 1000:
                unit = _unit
                break

        return '%.2f %s' % (pretty_size,
                unit)

    @property
    def stat(self):
        return os.stat(self.abspath)

    @property
    def ctime(self):
        return time.ctime(self.stat.st_ctime)

    @property
    def mtime(self):
        return time.ctime(self.stat.st_mtime)

    @property
    def isexist(self):
        return os.path.exists(self.abspath)

    @property
    def abspath(self):
        if self.relative_path[0] == '/':
            path = self.relative_path[1:]
        else:
            path = self.relative_path

        abspath = os.path.join(self.root, path)
        return abspath

class RedirectHandler(RequestHandler):
    def GET(self):
        self.redirect(**self.kwargs)

class FileHandler(RequestHandler):
    """
    列出所有本地所有文件及目录
    kwargs
        root: 本地文件目录
        show_hidden: 显示隐藏文件(默认False)
        hidden_list: 隐藏部分文件(正则表达式)
        deny_list: 禁止部分文件访问(正则表达式)
        deny_hidden: 禁止hidden_list的文件
        base_username: 401用户名
        base_password: 401密码
    """
    def init_data(self):
        hidden_list = self.kwargs.get('hidden_list', [])
        deny_list = self.kwargs.get('deny_list', [])

        if self.kwargs.get('deny_hidden'):
            deny_list.extend(hidden_list)

        self.hidden_re_list = [ re.compile(hidden_exp) for hidden_exp in hidden_list]
        self.deny_re_list = [re.compile(deny_exp) for deny_exp in deny_list]
        self.base_username = self.kwargs.get('base_username')
        self.base_password = self.kwargs.get('base_password')

    def GET(self, relative_path = '/'):
        if self.base_username and self.base_password:
            auth_401(self.__class__._GET)(self, relative_path)

        else:
            self._GET(relative_path)

    def _GET(self, relative_path):
        relative_path = relative_path or '/'
        if relative_path.startswith('./'):
            self.raise_error(403)

        self.relative_path = relative_path

        item = _FileItem(self.root, relative_path)
        if not (item.isexist and self.allow_account(item)):
            self.raise_error(404)

        elif item.isfile:
            self.set_header('Content-Type', get_mime_type(item.abspath))
            self.send_file(item.abspath, is_attr = self.query.attr == '1')
        else:
            self.render('files.html', items = self.ls(item.dirname), 
                    relative_path = relative_path, parent = item.dirname)

    def get_current_user(self):
        username, password = self.get_401_user_pwd()
        if username == self.base_username and password == self.base_password:
            return username

        else:
            return None

    def allow_account(self, item):
        item_urlpath = os.path.join(self.relative_path, item.pretty_name)
        return not any([deny_re.search(item_urlpath) for deny_re in self.deny_re_list])

    def allow_show(self, item):
        allow_hiddent = self.kwargs.get('show_hidden', False)
        if (not allow_hiddent) and item.ishidden:
            return False

        item_urlpath = os.path.join(self.relative_path, item.pretty_name)
        return not any([hidden_re.search(item_urlpath) for hidden_re in self.hidden_re_list])

    def ls(self, dir_path):
        items = []

        for item_name in os.listdir(dir_path):
            new_item = _FileItem(dir_path, item_name)


            if not self.allow_show(new_item):
                continue

            items.append(new_item)

        return items

    @property
    def root(self):
        return self.kwargs.get('root', '/')

    def get_template_path(self):
        return self._generate_abspath('template')

class ErrorHandler(RequestHandler):
    def ALL(self):
        status_code = self.kwargs.get('status_code', 500)
        raise HTTPError(status_code)

class Application(object):
    _buffer_stringio = s_io()
    _template_cache = {}

    def __init__(self, handlers = [], vhost_handlers = [], settings = {}, log_settings = {},  ui_settings = {}):
        """
        log_settings : {'level': log level(default: DEBUG',
                'datefmt': log date format(default: "%Y-%m-%d %H:%M:%S"),
                'file': log save to file}
        ui_settings: {module_name: module(extends from UIModule)}
        """
        self.settings = settings
        self.ui_settings = ui_settings
        default_handlers = []

        if settings.get('static_path'):
            static_class = settings.get('static_class', StaticFileHandler)
            for url_re in (r'%s(.*)' %
                (settings.get('static_prefix', r'/static/')),
                r'/(favicon\.ico)', r'/(robots\.txt)'):
                default_handlers.append((url_re, static_class))

        gale_static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                'static')

        if settings.get('debug'):
            _debug_prefix = settings.get('debug_prefix', '/')
            _debug_handler_url = os.path.join(_debug_prefix, 'gale/debug')
            _debug_static_url = os.path.join(_debug_prefix, 'gale/static')

            default_handlers.append((_debug_handler_url, DebugHandler, 
                {'static_url_path': _debug_static_url}))

            default_handlers.append((r'%s/(.*)' % (_debug_static_url),
                StaticFileHandler, {'root_path': 
                    gale_static_path}))

        if 'session_manager'  in settings:
            self.session_manager = settings['session_manager']

        vhost_handlers = vhost_handlers or [('.*$', handlers)]
        self.vhost_handlers = []
        for _vhost_handler in vhost_handlers:
            self.add_handlers(*_vhost_handler)

        # 缺省的一些handler被从vhost_handlers中分离出来, 使缺省的handler应用到所有的host handlers中去
        self.default_handlers = []
        for default_handler in default_handlers:
            if len(default_handler) == 2:
                _url, _hdl = default_handler
                self.default_handlers.append([self.__re_compile(_url),
                    _hdl, {}])

            elif len(default_handler) == 3:
                _url, _hdl, _kwargs = default_handler
                self.default_handlers.append([self.__re_compile(_url),
                    _hdl, _kwargs])

        config_logging(log_settings)

    def __re_compile(self, re_string):
        """把正则规则都编译了，加快速度"""
        re_string = "%s%s%s" % ((not re_string.startswith('^')) and '^' or '', 
            re_string, (not re_string.endswith('$')) and '$' or '')  # 自动给url加上开头与结尾
        return re.compile(re_string)

    def add_handlers(self, re_host_string, host_handlers, to_handlers = None):
        to_handlers = self.vhost_handlers if to_handlers == None else to_handlers
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
            to_handlers.insert(-1, (self.__re_compile(re_host_string), _compile_handlers))
    
    def __call__(self, request, is_wsgi = False, server_settings = None):
        if not request: # 如果无法获取一个request，则结束它，表示连接已经断开
            return

        self.server_settings = server_settings or {}

        request.real_ip = self.settings.get('real_ip', True) # 设定是否要获取真实ip地址

        handler, url_args, url_kwargs = self.__find_handler(request)
        url_args = map(urlunquote, url_args)
        try:
            self.__exec_request(handler, request, *url_args, **url_kwargs)
        except Exception as e:
            handler.process_raise_error(e) # 把异常传入，并分析，执行错误处理方法(push_error)
            if handler.get_status() >= 500: # 只有错误代码大于等于500才会打印出异常信息
                traceback.print_exc()
        finally:
            if (not is_wsgi) and (getattr(handler, '_is_auto_finish', False) == False):
                handler.finish()

        return handler


    def __exec_request(self, handler, request, *args, **kwargs):
        handler.ALL(*args, **kwargs) #  所有请求前都要先执行它
        _method_func = getattr(handler, request.method, None) 
        if not _method_func:
            handler.set_header('Allow', 
                    ', '.join(handler.allow_methods))
            raise NotSupportMethod

        _method_func(*args, **kwargs)

    def __find_handler(self, request):
        """根据url来决定将任务交由哪个handler去处理, 会返回handler，还有url参数"""
        request_path = request.path
        request_host = request.host

        for vhost_re, handlers in self.vhost_handlers: # 如果启用了虚拟主机，则做一下host字段的匹配
            if vhost_re.match(request_host):
                self.handlers = handlers
                break

        for url_re, url_handler, kwargs in self.handlers + self.default_handlers:
            _match = url_re.match(request_path)
            if _match: # 如果匹配上了，就执行下一步
                return url_handler(self, request, kwargs = kwargs), _match.groups(), _match.groupdict()

        default_handler = self.settings.get('default_handler')
        if default_handler: # 如果指定了默认处理，则调用，否则让ErrorHandler处理它，也就是会被当404处理
            return default_handler(self, request), (), {}
        else:
            return ErrorHandler(self, request, kwargs = {'status_code': 404}), (), {}


    def router(self, url, method = None, base_handler = None, host = '^.*$', kwargs = None, is_login = False, should_login = False, bind_methods = None, handler = None):
        assert not (is_login and should_login) # 同时是登录类，又需要登录，这怎么可能呢

        bind_methods = bind_methods or {}

        base_handler =  handler or self.__made_base_handler(host, url, base_handler) # 根据url来生成一个类

        for method_name, method_instance in bind_methods.items():
            setattr(base_handler, method_name, method_instance)


        method = method or 'GET'
        kwargs = kwargs or {}

        if handler:
            self.add_handlers(host, [(url, handler, kwargs), ])
            return

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

        _m = hashlib.md5(utf8(url))
        _class_name = '_T%s_Handler' % (_m.hexdigest())
        return type(native_str(_class_name),
                (base_handler or RequestHandler, ), {})

    def run(self, host = '', port = 8080, processes = 0, **server_settings):
        http_server = HTTPServer(self, 
                host = host, port = port,
                **server_settings)
        http_server.run(processes)

    @property
    @cache.cache_self
    def _static_md5_cache(self):
        if self.server_settings['processes'] == 1:
            return {}
        else:
            return IPCDict('_static_md5_cache')

def limit_referrer(method):
    """防外链"""
    @wraps(method)
    def wrap(self, *args, **kwargs):
        referrer = self.request.get_header('referrer')
        referrer_host = referrer and urlsplit(referrer).netloc.split(':')[0]
        if (not referrer) or referrer_host != self.request.host:
            self.on_referrer_error()
            return

        return method(self, *args, **kwargs)
    
    return wrap

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

def async(method):
    @wraps(method)
    def wrap(self, *args, **kwargs):
        self._is_auto_finish = True
        return method(self, *args, **kwargs)

    return wrap


class UIModule(object):
    def __init__(self, handler):
        self.handler = handler
        self.request = handler.request

    def render(self):
        raise NotImplementedError

    def render_string(self, template_name, *args, **kwargs):
        return self.handler.render_string(template_name, *args, **kwargs)

    def string_render(self, string, *args, **kwargs):
        return self.handler.string_render(string, *args, **kwargs)


class StaticFileHandler(RequestHandler):
    absolute_path = None
    def HEAD(self, file_path):
        return self.GET(file_path, is_include_body = False)

    def get_static_root_path(self):
        static_root_path = self.kwargs.get('root_path') or self.static_path

        return static_root_path

    def GET(self, file_path, is_include_body = True):
        self.__is_sending_file = True
        absolute_path = self.make_absolute_path(self.get_static_root_path(),
                file_path)
        if not os.path.exists(absolute_path):
            raise HTTPError(404)

        self.absolute_path = absolute_path

        self.set_header('Content-Type', get_mime_type(self.absolute_path))

        if self.get_content_size() < 1024 * 1024 * 10: # 10m以下的文件才做缓存
            content_version = self.get_content_version(absolute_path)

            self.set_expire_header()
            self.set_etag_header(content_version)

            is_return_304 = self.should_return_304(content_version)
        else:
            is_return_304 = False

        if is_return_304:
            self.set_status(304)
        else:
            self.set_header('Content-Length', self.get_content_size())

        if is_include_body and (not is_return_304): # 如果是Flase，则表示是HEAD方法传过来的，这时候不需要发送文件
            for _data in self.get_content(absolute_path):
                self.push(_data)
                self.flush()

    def get_content_size(self):
        return self.file_stat().st_size

    def should_return_304(self, content_version):
        """判断是否需要返回304,判断下request中的内容hash值与计算出来的是否一样就行了"""
        cache_control = self.request.get_header('Cache-Control')
        if cache_control == 'no-cache':
            return False
        return self.get_request_version() == content_version

    def get_request_version(self):
        """获取request中的内容hash值"""
        version = self.request.headers.get('If-None-Match', '')
        return version

    def process_buffer(self, _buffer):
        return _buffer

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


    def set_expire_header(self):
        """这是在设置跟过期有关的http头"""
        expire_sec = 86400 * 365 * 10
        if self.is_supported_http1_1():
            self.set_header('Cache-Control', 'max-age=%s' % (expire_sec))
        else:
            self.set_header('Expires', format_timestamp(time.time() + expire_sec))


    def get_content_version(self, absolute_path):
        _cache_version = self.get_cache_version(absolute_path)
        if _cache_version:
            return _cache_version

        md5er = hashlib.md5()
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

    def set_etag_header(self, etag = None):
        if not self.is_supported_http1_1(): # 如果不是http 1.1则是不支持的（比如 1.0)
            return 

        etag = etag or self.get_content_version(self.absolute_path)
        self.set_header('Etag', etag)


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
        _buffer_stringio.truncate()

        response_headers['Content-Encoding']  = 'gzip'

        return compression_data

class _UINameSpace(object):
    def __init__(self, handler):
        self.handler = handler
    
    def __getattr__(self, module):
        _module = self.handler.ui_settings.get(module)
        _module_instance = _module(self.handler)
        return _module_instance.render

def create_cookie_signature(secret, value_b64encoded):
    hash_obj = hmac.new(utf8(secret), value_b64encoded, digestmod =  hashlib.sha256)
    return utf8(hash_obj.hexdigest()).upper()

def encode_signed_cookie(secret, name, value):
    name = utf8(name)
    value = utf8(value)
    value = base64.b64encode(value)
    signed_secret = create_cookie_signature(secret, value)
    signed_cookie = "|%s:%s|%s:%s%s" %(
            len(name), name, len(value), value, signed_secret)

    return signed_cookie

def decode_signed_cookie(secret, name, value):
    assert value[0] == '|'
    signed_cookie = value
    def split_signed_cookie(rest):
        offset = rest.find(':')
        field_length = int(rest[1: offset])
        field_value = rest[offset + 1: offset + field_length + 1]

        rest = rest[field_length + offset + 1: ]

        return field_value, rest

    try:
        field_name, rest = split_signed_cookie(signed_cookie)
        field_value, rest = split_signed_cookie(rest)
    except ValueError:
        return None


    if create_cookie_signature(secret, field_value) != rest:
        return None

    return base64.b64decode(field_value)

def decode_signed_cookie_tornado(secret, name, value):
    signed_cookie = value
    rest = signed_cookie[2:]
    def split_signed_cookie(rest):
        offset = rest.find(b':')
        length = int(rest[0: offset])
        field_value = rest[offset + 1: length + offset + 1]

        rest = rest[length + offset + 2:]

        return field_value, rest

    key_version, rest = split_signed_cookie(rest)
    timestamp, rest = split_signed_cookie(rest)
    field_name, rest = split_signed_cookie(rest)
    field_value, rest = split_signed_cookie(rest)

    if int(timestamp) < int(time.time()) - 30 * 86400:
        return None

    return base64.decodestring(field_value)

class ParamsObject(object):
    def __init__(self, params):
        self._params =  params

    def __getitem__(self, name):
        value = self._params.get(name, None)
        if value == None:
            return None

        return value[0]

    def __getattr__(self, name):
        return self[name]

    def __repr__(self):
        return json.dumps(self._params, indent = 4)

class BodyParamsResponseObject(ParamsObject):
    def __init__(self, params):
        self._buffer = []
        super(BodyParamsResponseObject, self).__init__(params)

    def append_buffer(self, _buffer):
        self._buffer.append(utf8(_buffer))

    def set_buffer(self, _buffer):
        self._buffer = []

        if not _buffer:
            self.append_buffer(_buffer)

    def empty(self):
        return self._buffer == []

    def to_bytes(self):
        return b''.join(self._buffer)

    def __add__(self, _buffer):
        self.append_buffer(_buffer)

    def flush_buffer(self):
        self._buffer = []

class DebugHandler(RequestHandler):
    def ALL(self):
        if not self.settings.get('debug'):
            raise HTTPError(404)

        self.restapi = RestApi(self.application.vhost_handlers)

    def GET(self):
        restapi_list = self.restapi.generate_restapi_list()

        api_module_tree = list(restapi_list.keys())
        self.render('doc.html', api_description = '', api_module_tree = api_module_tree,
                api_docs = restapi_list, 
                cat_response_params = self._cat_response_params,
                cat_request_params = self._cat_request_params)


    def get_static_url(self, file_path):
        static_url_path = self.kwargs['static_url_path']
        return os.path.join(static_url_path, file_path)

    def _cat_response_params(self, response_params):
        response_params = response_params or {}
        public_response_params = self.settings.get('restapi_public_response', {})
        response_params.update(public_response_params)

        return response_params

    def _cat_request_params(self, request_params):
        if not request_params:
            return {}
        public_request_params = self.settings.get('restapi_public_request', {})
        request_params.update(public_request_params)
        return request_params


    def get_template_path(self):
        return self._generate_abspath('template')

from gale.server import HTTPServer

@single_pattern
class _HANDLER_LIST(list):
    pass

HANDLER_LIST = _HANDLER_LIST()

def router(*args, **kwargs):
    def wraps(method_func = None):
        HANDLER_LIST.append((method_func, args, kwargs))

    handler = kwargs.get('handler')

    if handler:
        wraps()
    else:
        return wraps

def app_run(app_path = None, settings = {}, log_settings={}, server_settings = {}, host = '', port = 8080, processes = 0):
    """在这里的app_path决定着默认template和static_path，默认是执行脚本程序时的工作目录"""
    settings.setdefault('debug', True)
    settings.setdefault('static_path', os.path.join(app_path and os.path.dirname(os.path.abspath(app_path)) or os.getcwd(), 'static'))
    settings.setdefault('template_path', os.path.join(app_path and os.path.dirname(os.path.abspath(app_path)) or os.getcwd(), 'template'))

    app = Application(settings = settings, 
            log_settings = log_settings)

    for handler_func, args, kwargs in HANDLER_LIST:
        if handler_func:
            app.router(*args, **kwargs)(handler_func)
        else:
            app.router(*args, **kwargs)

    http_server = HTTPServer(app, host = host, port = port, **server_settings)
    http_server.run(processes = processes)

