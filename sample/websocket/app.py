#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-09-10 19:16:35
# Filename      : app.py
# Description   : 
from gale.web import Application
from gale.websocket import WebSocketHandler

class ConnHandler(WebSocketHandler):
    clients = {}
    def on_open(self):
        pass

    def on_message(self, frame):
        message = frame.data
        if self not in ConnHandler.clients: # 表示这是新用户
            ConnHandler.clients[self] = message # 这里的message就是用户的nickname
            self.broadcast('system', '欢迎 {nickname} 进入聊天室'.format(nickname = message))
        else:
            self.broadcast(ConnHandler.clients[self], message)

    def on_close(self):
        nickname = ConnHandler.clients.pop(self)
        self.broadcast('system', '{nickname} 离开了聊天室'.format(nickname = nickname))

    def broadcast(self, _from, message):
        for client in ConnHandler.clients:
            client.send_message('{_from}: {message}'.format(_from = _from,
                message = message))

app = Application([(r'/conn', ConnHandler)],
        settings = {'debug': True, 
            'template_path': 'template',
            'static_path': 'static'})

@app.router('/')
def index(self):
    self.render('index.html')

app.run(port = 5000, processes = 1)

