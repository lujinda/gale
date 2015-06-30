#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-09 10:03:05
# Filename      : helloword.py
# Description   : 
from __future__ import unicode_literals
from gale.web import app_run, router
from gale.utils import ShareDict
import uuid

all_files = ShareDict()
"""
@router(url='/')
def index(self):
    self.render('index.html')

@router(url='/file', method='GET')
def file_get(self):
    uuid = self.get_argument('uuid', '')
    _file = all_files.get(uuid)
    if not _file:
        self.set_status(404)
        return
    self.push(_file)

@router(url='/file', method='POST')
def file_post(self):
    _result = {'error': ''}
    img = self.get_file('img')
    if 'image' not in img.content_type:
        _result['error'] = '上传的文件不是图片哦'
        self.push(_result)
        return

    file_uuid = uuid.uuid4().hex
    all_files[file_uuid] = img.body
    _result['img_url'] = '/file?uuid='  + file_uuid

    self.push(_result)

app_run(__file__)

"""
import os
import uuid
from public import MyRequestHandler

all_files = {}

class IndexHandler(MyRequestHandler):
    def GET(self):
        self.render('index.html')

class FileHandler(MyRequestHandler):
    def GET(self):
        uuid = self.get_argument('uuid', '')
        _file = all_files.get(uuid)
        if not _file:
            self.set_status(404)
            return
        self.set_header('Content-Type', _file.content_type)
        self.push(_file.body)

    def POST(self):
        _result = {'error': ''}
        img = self.get_file('img')
        if 'image' not in img.content_type:
            _result['error'] = '上传的文件不是图片哦'
            self.push(_result)
            return

        file_uuid = uuid.uuid4().hex
        all_files[file_uuid] = img
        _result['img_url'] = '/file?uuid='  + file_uuid

        self.push(_result)
