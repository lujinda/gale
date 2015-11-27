#!/usr/bin/env python
#coding:utf8
# Author          : tuxpy
# Email           : q8886888@qq.com
# Last modified   : 2015-03-25 14:18:30
# Filename        : gale/e.py
# Description     : 

class HeaderFormatError(Exception):
    pass

class DocParserError(Exception):
    pass

class HTTPError(Exception):
    def __init__(self, status_code, status_mess=None):
        self.status_code = status_code
        self.status_mess = status_mess
        super(HTTPError, self).__init__()


class ErrorStatusCode(Exception):
    pass

class MissArgument(Exception):
    pass

class NotSupportHttpVersion(Exception):
    pass

class LoginHandlerNotExists(Exception):
    pass

class LocalPathNotExist(Exception):
    pass

class CookieError(Exception):
    pass

class CacheError(Exception):
    pass

class HasFinished(Exception):
    pass

class WebSocketError(Exception):
    pass

class IPCError(Exception):
    pass

class JSONError(Exception):
    pass

class NotSupportStrategy(Exception):
    pass

class WorkerOffline(Exception):
    pass


NotSupportMethod = HTTPError(405)

