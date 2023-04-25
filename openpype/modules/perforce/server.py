# -*- coding: utf-8 -*-
"""Handling startup and shutdown of P4 RPC server."""
from __future__ import annotations

import threading
import aiohttp

from aiohttp import web
from aiohttp_json_rpc import JsonRpc
import asyncio
from openpype.lib import Logger

from .p4_client_wrapper import P4ClientWrapper


async def p4_run(project_name: str, command: str, args: list, client_required: bool):
    import web_pdb; web_pdb.set_trace()
    p4_client = P4ClientWrapper(project_name)
    return p4_client.p4_run(command, args, client_required)

async def p4_create_or_load_openpype_changelist(
            project_name: str, changelist_desc: str, changelist_identity: str | None,
            changelist_files: list[str] | None = None):
    p4_client = P4ClientWrapper(project_name)
    return p4_client.p4_create_or_load_openpype_changelist(changelist_desc, changelist_identity, changelist_files)

class P4ServerManager:
    """Manger that care about web server thread."""

    def __init__(self, port=None, host=None):
        self._log = None

        self.port = port
        self.host = host or "localhost"

        self.client = None
        self.handlers = {}
        self.on_stop_callbacks = []

        loop = asyncio.get_event_loop()

        rpc = JsonRpc(loop=loop)
        rpc.add_methods(
            ('', p4_run),
            ('', p4_create_or_load_openpype_changelist)
        )

        self.app = web.Application()
        self.app.router.add_route('*', '/rpc', rpc.handle_request)
        self.p4_server_thread = P4ServerThread(self)

    @property
    def log(self):
        if self._log is None:
            self._log = Logger.get_logger(self.__class__.__name__)
        return self._log

    @property
    def url(self):
        return f"http://{self.host}:{self.port}/rpc"

    def start_server(self):
        if self.p4_server_thread and not self.p4_server_thread.is_alive():
            self.p4_server_thread.start()

    def stop_server(self):
        if not self.is_running:
            return
        try:
            self.log.debug("Stopping Web server")
            self.p4_server_thread.is_running = False
            self.p4_server_thread.stop()

        except Exception:
            self.log.warning(
                "Error has happened during Killing Web server",
                exc_info=True
            )

    @property
    def is_running(self):
        if not self.p4_server_thread:
            return False
        return self.p4_server_thread.is_running

    def thread_stopped(self):
        for callback in self.on_stop_callbacks:
            callback()


class P4ServerThread(threading.Thread):
    """ Listener for requests in thread."""

    def __init__(self, manager):
        self._log = None

        super(P4ServerThread, self).__init__()

        self.is_running = False
        self.manager = manager
        self.loop = None
        self.runner = None
        self.site = None
        self.tasks = []

    @property
    def log(self):
        if self._log is None:
            self._log = Logger.get_logger(self.__class__.__name__)
        return self._log

    @property
    def port(self):
        return self.manager.port

    @property
    def host(self):
        return self.manager.host

    def run(self):
        self.is_running = True

        try:
            self.log.info(">>> Starting Perforce RPC server")
            self.loop = asyncio.new_event_loop()  # create new loop for thread
            asyncio.set_event_loop(self.loop)

            self.loop.run_until_complete(self.start_server())

            self.log.debug(
                ("*** Running Perforce RPC server on "
                 f"URL: \"localhost:{self.port}\"")
            )

            asyncio.ensure_future(self.check_shutdown(), loop=self.loop)
            self.loop.run_forever()

        except Exception:
            self.log.warning(
                "!!! Perforce RPC service has failed", exc_info=True
            )
        finally:
            self.loop.close()  # optional

        self.is_running = False
        self.manager.thread_stopped()
        self.log.info("...Perforce RPC server stopped")

    async def start_server(self):
        """ Starts runner and TCPsite """
        self.runner = web.AppRunner(self.manager.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

    def stop(self):
        """Sets is_running flag to false, 'check_shutdown' shuts server down"""
        self.is_running = False

    async def check_shutdown(self):
        """ Future that is running and checks if server should be running
            periodically.
        """
        while self.is_running:
            while self.tasks:
                task = self.tasks.pop(0)
                self.log.debug(f"  - waiting for task {task}")
                await task
                self.log.debug(f"  - returned value {task.result}")

            await asyncio.sleep(0.5)

        self.log.debug(">>> Starting Perforce RPC shutdown")
        await self.site.stop()
        self.log.debug("  - Site stopped")
        await self.runner.cleanup()
        self.log.debug("  - Runner stopped")
        tasks = [
            task
            for task in asyncio.all_tasks()
            if task is not asyncio.current_task()
        ]
        list(map(lambda task: task.cancel(), tasks))  # cancel all the tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        self.log.debug(
            f'Finished awaiting cancelled tasks, results: {results}...'
        )
        await self.loop.shutdown_asyncgens()
        # to really make sure everything else has time to stop
        await asyncio.sleep(0.07)
        self.loop.stop()
