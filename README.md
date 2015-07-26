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

# 对session的支持

直接在handler中直接使用self.session就行了。save，表示写入session信息，self.session的操作跟dict一样。默认是采用了文件来存session信息，如想用redis来存，只需要设置一下application的session_manager为RedisSessionManager的实例化对象就行

# 对cache的支持

需要在application中的settings中设置cache_manager，值可以是MemCacheManager（会存在内存中, 也可以是RedisCacheManager(可以存在redis中)。当然也可以放一个tuple，把这两都写进去，最后通过on参数来指定用谁。

