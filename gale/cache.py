#/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-09 08:38:20
# Filename      : cache.py
# Description   : 
import time

class MemCacheModel(object):
    cache = {}
    cache_key = []
    def __init__(self, max_length = 1000):
        self.max_length = max_length

    def set(self, key, value, ex = 86400):
        if len(self.cache_key) > self.max_length:
            _old_key = self.cache_key.pop(0)
            del self.cache[key]
        
        if not self.cache.has_key(key): # 如果key不存在于self.cache中，则表示这是新加的，需要把key添加到列表中去
            self.cache_key.append(key)

        self.cache[key] = {'value': value, 'ex': ex + time.time()}

        assert len(self.cache) == len(self.cache_key)

    def get(self, key):
        assert len(self.cache) == len(self.cache_key)
        if not self.cache.has_key(key):
            return None
        else:
            _cache_value = self.cache[key]
            self.cache_key.remove(key)

            if time.time() > _cache_value['ex']: # 如果已经过期了，则就删除它
                del self.cache[key]
                return None

            self.cache_key.append(key)

            return _cache_value['value']

