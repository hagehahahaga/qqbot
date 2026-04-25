import tornado.websocket
import tornado.web
from abstract.bases.importer import json, coredumpy, sys, threading
from abstract.bases.custom_thread import CustomThread

from abstract.bases.log import *
from abstract.bot import BOT


class OneBotHttpClient:
    class RootHandler(tornado.web.RequestHandler):
        def get(self):
            self.redirect('/status')
        
        def post(self):
            data = json.loads(self.request.body)
            CustomThread(
                target=BOT.router,
                args=(data,),
                daemon=True
            ).start()
            self.write(json.dumps({}))

    class WebHandler(tornado.web.RequestHandler):
        def get(self):
            self.write(pathlib.Path('web/index.html').read_text(encoding='utf-8'))

    class ServiceStatusHandler(tornado.web.RequestHandler):
        def get(self):
            self.write(
                json.dumps(
                    {
                        service_name: BOT.services[service_name].is_alive() for service_name in BOT.services
                    }
                )
            )

    class WebSocketHandler(tornado.websocket.WebSocketHandler):
        clients: set[tornado.websocket.WebSocketHandler] = set()

        def open(self):
            # 将当前连接的客户端添加到集合中
            self.clients.add(self)
            for log in LOGS_HISTORY:
                self.write_message(log)

        def on_close(self):
            # 从集合中移除当前断开的客户端
            self.clients.remove(self)

        def check_origin(self, origin):
            # 允许所有跨域请求
            return True

    def __init__(self):
        self.app = tornado.web.Application(
            [
                ('/', self.RootHandler),
                ('/status', self.WebHandler),
                ('/websocket', self.WebSocketHandler),
                ('/api/services_status', self.ServiceStatusHandler)
            ],
            static_path=pathlib.Path('web/static')
        )
        CustomThread(
            target=self.auto_post_logs
        ).start()
        self.app.listen(8000)
        self.loop = tornado.ioloop.IOLoop.current()

    def auto_post_logs(self):
        while True:
            log = LOGS_UPDATE_QUEUE.get()
            for client in self.WebSocketHandler.clients:
                try:
                    self.loop.add_callback(client.write_message, log)
                except:
                    self.WebSocketHandler.clients.remove(client)

    def start(self):
        LOG.INF('Server starting up.')
        # Save original before coredumpy patch
        original_sys_excepthook = sys.excepthook
        # Patch both main thread and thread exceptions
        coredumpy.patch_except(directory='./dumps')
        # Wrap sys.excepthook to ignore KeyboardInterrupt
        coredump_sys_excepthook = sys.excepthook
        def _sys_excepthook(type, value, tb):
            if type is KeyboardInterrupt:
                original_sys_excepthook(type, value, tb)
            else:
                coredump_sys_excepthook(type, value, tb)
        sys.excepthook = _sys_excepthook
        
        # Also patch threading.excepthook for thread exceptions
        def _threading_excepthook(args):
            if args.exc_type is KeyboardInterrupt:
                return
            sys.excepthook(args.exc_type, args.exc_value, args.exc_traceback)
        
        threading.excepthook = _threading_excepthook
        self.loop.start()


FRAME_CLIENT = OneBotHttpClient()
