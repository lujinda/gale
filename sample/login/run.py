#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-09 15:20:13
# Filename      : test.py
# Description   : 
from gale.web import app_run, router, RequestHandler

class BaseHandler(RequestHandler):
    def get_current_user(self):
        return self.session.get('username')

@router(url = '/login', is_login = True, base_handler = BaseHandler)
def login(self):
    self.render('login.html')

@router(url = '/login', method = 'POST', base_handler = BaseHandler)
def login_post(self):
    username = self.get_argument('username', '')
    if username:
        self.session['username'] = username
        self.session.save()
    callback_url = self.get_query_argument('callback', '/')
    self.redirect(callback_url)

@router(url = '/logout', method='GET', base_handler = BaseHandler)
def logout(self):
    self.session.pop('username', None)
    self.session.save()
    self.redirect('/')

@router(url = '/', base_handler = BaseHandler, should_login = True)
def index(self):
    self.push('hi ' + self.current_user)


app_run(__file__)

