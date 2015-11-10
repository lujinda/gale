#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy # Email         : q8886888@qq.com.com
# Last modified : 2015-06-09 08:38:20
# Filename      : cache.py
# Description   : 
from collections import OrderedDict
from gale.e import CacheError
import time
import hashlib
from gale.escape import utf8
from functools import wraps
try:
    import cPickle as pickle
except ImportError:
    import pickle

class ICacheManager(object):
    def get(self, key): 
        """获取cache""" 
        raise NotImplementedError

    def set(self, key, value, expire = None):
        """设置一个cache,可传入key和expire"""
        raise NotImplementedError

    def flush_all(self):
        """清空所有缓存"""
        raise NotImplementedError

    def flush(self, key):
        """清删除某个key"""
        raise NotImplementedError

    @property
    def __name__(self):
        raise NotImplementedError

class MemCacheManager(ICacheManager):
    """基于内存的使用lru算法"""
    _cache_dict = OrderedDict() # 这是为了对那些不经常访问的数据做删除，所以要用到有序的dict
    _expire_dict = OrderedDict()  # 存过期时间的map
    def __init__(self, expire = 7200, max_size = 100):
        self.expire = expire
        self.max_size = max_size

    def set(self, key, value, expire = None):
        self.flush(key)
        expire = expire or self.expire
        assert isinstance(expire, int)
        self._cache_dict[key] = value
        self._expire_dict[key] = int(time.time()) + expire
        self.clearup()
        
    def flush(self, key):
        if key in self._cache_dict:
            del self._cache_dict[key]
            del self._expire_dict[key]

    def flush_all(self):
        self._cache_dict.clear()
        self._expire_dict.clear()

    def get(self, key):
        self.clearup()
        return self._cache_dict.get(key, None)

    def ttl(self, key):
        ttl = self._expire_dict.get(key) or 0
        return ttl

    def clearup(self):
        now = int(time.time())
        for key in self._expire_dict:
            if now > self._expire_dict[key]:
                self.flush(key)
            else:
                break # 因为是根据插入的次序排的，有一个不过期，就说明后面的都不会过期了。

        while len(self._cache_dict) > self.max_size:
            for key in self._cache_dict:
                self.flush(key)
                break

    @property
    def __name__(self):
        return 'mem'

class RedisCacheManager(ICacheManager):
    def __init__(self, db, expire = 7200, prefix = None):
        self.expire = expire
        self.db = db
        self.prefix = prefix or 'gale:redis_cache:'

    def set(self, key, value, expire = None):
        key = self.prefix + utf8(key)
        expire = expire or self.expire
        value = pickle.dumps(value, protocol = 1)

        pipe = self.db.pipeline()
        pipe.set(key, value)
        pipe.expire(key, expire)
        result_list = pipe.execute()

        for result in result_list:
            assert result

    def get(self, key):
        key = self.prefix + utf8(key)
        value = self.db.get(key)
        if not value:
            return None

        value = pickle.loads(value)

        return value

    def ttl(self, key):
        key = self.prefix + utf8(key)

        return self.db.ttl(key) or 0

    def flush_all(self):
        pipe = self.db.pipeline()
        for key in self.db.keys(self.prefix + '*'):
            pipe.delete(key)

        pipe.execute()

    def flush(self, key):
        self.db.delete(key)

    @property
    def __name__(self):
        return 'redis'

def _generate_key(key, args, kwargs):
    m = hashlib.md5(utf8(key))
    [m.update(utf8(str(arg))) for arg in args]
    [m.update(utf8("%s=%s" % tuple(item))) for item in kwargs.items()]

    return m.hexdigest()

def cache(key = None, expire = None, on = None):
    """on表示cache存在哪，可选mem,和redis，如果没有选，则默认"""
    def outer_wrap(func):
        def inner_wrap(hdl, *args, **kwargs):
            cache_manager = hdl.get_cache_manager(on)
            _key = key or (func.__name__ + hdl.__class__.__name__ + hdl.__module__)
            _key = _generate_key(_key, args, kwargs)
            cache = cache_manager.get(_key)
            if cache:
                return cache

            value = func(hdl, *args, **kwargs)
            cache_manager.set(_key, value, expire)

            return value

        return inner_wrap

    return outer_wrap

def page(expire = None, on = None):
    def outer_wrap(func):
        @wraps(func)
        def inner_wrap(hdl, *args, **kwargs):
            if hdl.request.method != 'GET':
                raise CacheError('page cache only support GET method')
            cache_manager = hdl.get_cache_manager(on)
            _key = hdl.request.uri
            cache = cache_manager.get(_key)
            if cache and cache['status'] in (200, 304):
                hds = cache['headers']
                hdl.set_header('Content-Type', hds['Content-Type'])
                hdl.set_header('Server', 'Gale Cache')
                hdl.set_status(200)
                hdl.push(cache['body'])
                return 

            hdl.cache_page = True
            result = func(hdl, *args, **kwargs)
            hdl.flush()
            if hdl.response_body:  # 只在200和304时有body
                cache = {'status': hdl._status_code, 
                        'headers': hdl._headers, 'body': hdl.response_body}
                cache_manager.set(_key, cache, expire)

            return result

        return inner_wrap

    return outer_wrap

def cache_self(func):
    @wraps(func)
    def wrap(self):
        _key = '_cache_' + func.__name__[0]
        _cache = getattr(self, _key, None)
        if _cache:
            return _cache

        _value = func(self)
        setattr(self, _key, _value)

        return _value

    return wrap

