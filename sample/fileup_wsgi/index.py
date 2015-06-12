#/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-06-09 10:03:05
# Filename      : helloword.py
# Description   : 
from __future__ import unicode_literals
from gale.utils import ShareDict
from gale.wsgi import WSGIApplication
from wsgiref import simple_server
import uuid
import os

app = WSGIApplication(settings = {
    'template': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template'),
    'static_path': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'),
    })

all_files = ShareDict()
@app.router(url='/')
def index(self):
    self.render('index.html')

@app.router(url='/file', method='GET')
def file_get(self):
    uuid = self.get_argument('uuid', '')
    _file = all_files.get(uuid)
    if not _file:
        self.set_status(404)
        return
    self.push(_file)

@app.router(url='/file', method='POST')
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

server = simple_server.make_server('', 8080, app)
server.serve_forever()

