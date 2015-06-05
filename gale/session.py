#/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-04 11:28:26
# Filename      : session.py
# Description   : 
from __future__ import unicode_literals, print_function

import uuid
import threading
import hmac
try:
    import cPickle as pickle
except ImportError:
    import pickle

import hashlib
import os
import time

class SessionData(dict):
    def __init__(self, session_id, hmac_key):
        self.session_id = session_id
        self.hmac_key = hmac_key

class Session(dict):
    def __init__(self, session_manager, request_handler):
        self.session_manager = session_manager
        self.request_handler = request_handler

        try:
            current_session = session_manager.get(request_handler)
        except InvalidSessionException:
            current_session = session_manager.get()

        for key, data in current_session.iteritems():
            self[key] = data

        self.session_id = current_session.session_id
        self.hmac_key = current_session.hmac_key

    def save(self):
        self.session_manager.set(self.request_handler, self)

    def flush(self):
        self.session_manager.flush(self.request_handler, self)

class ISessionManager(object):
    def __init__(self):
        raise ImportError

    def get(self, request_handler = None):
        session_id = (request_handler and request_handler.get_cookie('SESSION_ID')) or self._generate_id()
        hmac_key = (request_handler and request_handler.get_cookie('VERIFICATION')) or self._generate_hmac(session_id)

        check_hmac = self._generate_hmac(session_id)
        if hmac_key != check_hmac:
            raise InvalidSessionException

        session = SessionData(session_id, hmac_key)
        session_data = self._fetch(session_id)
        session.update(session_data)

        return session

    def _fetch(self, session_id):
        raise ImportError

    def set(self, request_handler, session):
        request_handler.set_cookie('SESSION_ID', session.session_id)
        request_handler.set_cookie('VERIFICATION', session.hmac_key)
        self.save_session(session)

    def flush(self, request_handler, session):
        request_handler.clear_cookie('SESSION_ID')
        request_handler.clear_cookie('VERIFICATION')
        self.remove_session(session)

    def save_session(self, session):
        raise ImportError

    def remove_session(self, session):
        raise ImportError

    def _generate_id(self):
        _id = b'GALE%s' % hashlib.sha1(self.session_secret + str(uuid.uuid4())).hexdigest()
        return _id

    def _generate_hmac(self, session_id):
        return hmac.new(session_id.encode(), self.session_secret, hashlib.sha1).hexdigest()

class FileSessionManager(ISessionManager):
    """这是使用文件来实现的seession机制"""
    lock = threading.RLock()

    def __init__(self, session_secret, session_timeout, session_path = None):
        self.session_secret = session_secret
        self.session_timeout = session_timeout

        import tempfile
        session_path = session_path or tempfile.gettempdir()
        if not os.path.isdir(session_path):
            raise SessionPathNotExists('session path not exist')

        self.session_path = session_path
        self.SESSION_PREFIX = '_glab_sess_'

        # 启动一个监控session过期时间的程序

        _monitor = threading.Thread(target = self._session_monitor)
        _monitor.setDaemon(True)
        _monitor.start()

    def _session_monitor(self):
        while True:
            self.__check_session()
            time.sleep(3)

    def __check_session(self):
        import glob
        for session_file in glob.glob(os.path.join(self.session_path, self.SESSION_PREFIX) + '*'):
            _stat = os.stat(session_file)
            if time.time() > _stat.st_atime + self.session_timeout:
                os.remove(session_file)

    def _fetch(self, session_id):
        session_file = os.path.join(self.session_path, 
                '%s%s' % (self.SESSION_PREFIX, session_id))

        try:
            with open(session_file, 'rb') as session_fd:
                session_data = pickle.loads(session_fd.read())
        except IOError:
            return {}

        return isinstance(session_data, dict) and session_data or {}

    def save_session(self, session):
        session_file = os.path.join(self.session_path, 
                '%s%s' % (self.SESSION_PREFIX, session.session_id))
        session_data = pickle.dumps(dict(session.items()))

        with self.lock:
            with open(session_file, 'wb') as session_fd:
                session_fd.write(session_data)

    def remove_session(self, session):
        session_file = os.path.join(self.session_path, 
                '%s%s' % (self.SESSION_PREFIX, session.session_id))
        del session
        os.remove(session_file)

class SessionPathNotExists(Exception):
    pass

class InvalidSessionException(Exception):
    pass

