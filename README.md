#Hello World#
<pre>
from gale.web import router, app_run
"""
@router(url = r'/(\w+)?', host='localhost', method = 'GET')
def hello(self, name = None):
    self.push('hello ' + (name or 'XXX'))
app_run()
"""
# 下面这样也可以哦
from gale.web import Application, RequestHandler
from gale.server import HTTPServer
class HelloHandler(RequestHandler):
    def GET(self, name = None):
        self.push('hello ' + (name or 'XXX'))
app = Application(handlers = [(r'/(\w+)?', HelloHandler), ])
http_server = HTTPServer(app)
http_server.listen(8080)
http_server.run()
"""
</pre>