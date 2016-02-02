#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-04 11:28:26
# Filename      : session.py
# Description   : 
from __future__ import unicode_literals, print_function

from gale.escape import utf8

import uuid
import threading
import hmac
import json

import hashlib
import os
import time

class SessionData(dict):
    def __init__(self, session_id, hmac_key):
        self.session_id = session_id
        self.hmac_key = hmac_key
        dict.__init__(self)

class Session(SessionData):
    def __init__(self, session_manager, request_handler):
        self.session_manager = session_manager
        self.request_handler = request_handler

        try:
            current_session = session_manager.get(request_handler)
        except InvalidSessionException:
            current_session = session_manager.get()

        for key, data in current_session.items():
            self[key] = data

        self.session_id = current_session.session_id
        self.hmac_key = current_session.hmac_key

        dict.__init__(self)

    def __getattr__(self, name):
        if name not in self:
            raise AttributeError

        return self[name]

    def save(self):
        self.session_manager.set(self.request_handler, self)

    def flush(self):
        self.session_manager.flush(self.request_handler, self)

class ISessionManager(object):
    def __init__(self):
        raise ImportError

    def get(self, request_handler = None):
        session_id = (request_handler and request_handler.get_signed_cookie(self.session_id_key)) or self._generate_id()
        hmac_key = (request_handler and request_handler.get_signed_cookie(self.session_verify_key)) or self._generate_hmac(session_id)

        check_hmac = self._generate_hmac(session_id)
        if hmac_key != check_hmac:
            raise InvalidSessionException

        session = SessionData(session_id, hmac_key)
        session_data = self._fetch(session_id)
        session.update(session_data)

        return session

    def _fetch(self, session_id):
        raise NotImplementedError

    def set(self, request_handler, session):
        request_handler.set_signed_cookie(self.session_id_key, session.session_id, expires_day = 30)
        request_handler.set_signed_cookie(self.session_verify_key, session.hmac_key, expires_day = 30)
        self.save_session(session)

    def flush(self, request_handler, session):
        request_handler.clear_cookie(self.session_id_key)
        request_handler.clear_cookie(self.session_verify_key)
        self.remove_session(session)

    def save_session(self, session):
        raise NotImplementedError

    def remove_session(self, session):
        raise NotImplementedError

    def _generate_id(self):
        _id = 'GALE%s' % hashlib.sha1(utf8(self.session_secret) + utf8(str(uuid.uuid4()))).hexdigest()
        return _id

    def _generate_hmac(self, session_id):
        return hmac.new(utf8(session_id), utf8(self.session_secret), hashlib.sha1).hexdigest()

class FileSessionManager(ISessionManager):
    """这是使用文件来实现的seession机制"""
    lock = threading.RLock()

    def __init__(self, session_secret, session_timeout, session_path = None, session_id_key = 'SESSION_ID', session_verify_key = 'VERIFICATION'):
        self.session_secret = session_secret
        self.session_timeout = session_timeout
        self.session_id_key = session_id_key
        self.session_verify_key = session_verify_key

        import tempfile
        session_path = session_path or tempfile.gettempdir()
        if not os.path.isdir(session_path):
            raise SessionPathNotExists('session path not exist')

        self.session_path = session_path
        self.SESSION_PREFIX = '_glab_sess_'

        from gale.utils import ShareDict

        self.__file_map = ShareDict() # 文件的访问时间记录到一张hash表中去
        self.__made_file_map(self.__file_map)

    def __made_file_map(self, file_map):
        import glob
        for session_file in glob.glob(os.path.join(self.session_path, self.SESSION_PREFIX) + '*'):
            _stat = os.stat(session_file)
            if time.time() > _stat.st_atime + self.session_timeout:
                os.remove(session_file)
            else:
                file_map[session_file] = _stat.st_atime

    def __update_file_map(self, session_file):
        for session_file, session_atime in self.__file_map.items():
            if time.time()  > session_atime + self.session_timeout:
                os.remove(session_file)
                del self.__file_map[session_file]

        self.__file_map[session_file] = time.time() # 把刚访问的那个文件在表中的访问日期也更新掉

    def _fetch(self, session_id):
        session_file = os.path.join(self.session_path, 
                '%s%s' % (self.SESSION_PREFIX, session_id))

        self.__update_file_map(session_file) # 每次有访问信息进来的，就去检查下hash表

        try:
            with open(session_file, 'rb') as session_fd:
                session_data = json.loads(session_fd.read())
        except IOError:
            return {}

        return isinstance(session_data, dict) and session_data or {}

    def save_session(self, session):
        session_file = os.path.join(self.session_path, 
                '%s%s' % (self.SESSION_PREFIX, session.session_id))
        session_data = json.dumps(dict(session.items())) 

        with self.lock:
            with open(session_file, 'wb') as session_fd:
                session_fd.write(session_data)

    def remove_session(self, session):
        session_file = os.path.join(self.session_path, 
                '%s%s' % (self.SESSION_PREFIX, session.session_id))
        del session
        if os.path.exists(session_file):
            os.remove(session_file)

class RedisSessionManager(ISessionManager):
    def __init__(self, session_secret, session_timeout, session_db, 
            session_id_key = 'SESSION_ID', session_verify_key = 'VERIFICATION'):
        self.session_secret = session_secret
        self.session_timeout = session_timeout
        self.session_db = session_db
        self.session_id_key = session_id_key
        self.session_verify_key = session_verify_key

    def _fetch(self, session_id):
        raw_data = self.session_db.get(session_id)
        if not raw_data:
            return {}

        self.session_db.expire(session_id, self.session_timeout)

        session_data = json.loads(raw_data)
        return isinstance(session_data, dict) and session_data or {}

    def save_session(self, session):
        session_data = json.dumps(dict(session.items()))
        self.session_db.setex(session.session_id, session_data, self.session_timeout)

    def remove_session(self, session):
        self.session_db.delete(session.session_id)

class SessionPathNotExists(Exception):
    pass

class InvalidSessionException(Exception):
    pass

