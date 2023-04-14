from aiohttp.web import Application, run_app
from aiohttp_json_rpc import JsonRpc
from .p4_client_wrapper import P4ClientWrapper
import asyncio


async def p4v_run(project_name: str, command: str, args: list):
    p4_client = P4ClientWrapper(project_name)
    return p4_client.p4_run(command, *args)


class Server(object):

    def __init__(self, port: int):
        self.port = port
        self._app = None

    def start_server(self):
        loop = asyncio.get_event_loop()

        rpc = JsonRpc()
        rpc.add_methods(
            ('', p4v_run),
        )

        self._app = Application(loop=loop)
        self._app.router.add_route('*', '/', rpc.handle_request)
        run_app(self._app, host='0.0.0.0', port=self.port)

    def stop_server(self):
        self._app.shutdown()
