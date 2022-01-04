import threading
import asyncio
import logging

from aiohttp import web

from .jobs import JobQueue
from .job_queue_route import JobQueueResource
from .workers_rpc_route import WorkerRpc

log = logging.getLogger(__name__)


class WebServerManager:
    """Manger that care about web server thread."""
    def __init__(self, port, host, loop=None):
        self.port = port
        self.host = host
        self.app = web.Application()
        if loop is None:
            loop = asyncio.new_event_loop()

        # add route with multiple methods for single "external app"
        self.webserver_thread = WebServerThread(self, loop)

    @property
    def url(self):
        return "http://{}:{}".format(self.host, self.port)

    def add_route(self, *args, **kwargs):
        self.app.router.add_route(*args, **kwargs)

    def add_static(self, *args, **kwargs):
        self.app.router.add_static(*args, **kwargs)

    def start_server(self):
        if self.webserver_thread and not self.webserver_thread.is_alive():
            self.webserver_thread.start()

    def stop_server(self):
        if not self.is_running:
            return

        try:
            log.debug("Stopping Web server")
            self.webserver_thread.stop()

        except Exception as exc:
            print("Errored", str(exc))
            log.warning(
                "Error has happened during Killing Web server",
                exc_info=True
            )

    @property
    def is_running(self):
        if self.webserver_thread is not None:
            return self.webserver_thread.is_running
        return False


class WebServerThread(threading.Thread):
    """ Listener for requests in thread."""
    def __init__(self, manager, loop):
        super(WebServerThread, self).__init__()

        self._is_running = False
        self._stopped = False
        self.manager = manager
        self.loop = loop
        self.runner = None
        self.site = None

        job_queue = JobQueue()
        self.job_queue_route = JobQueueResource(job_queue, manager)
        self.workers_route = WorkerRpc(job_queue, manager, loop=loop)

    @property
    def port(self):
        return self.manager.port

    @property
    def host(self):
        return self.manager.host

    @property
    def stopped(self):
        return self._stopped

    @property
    def is_running(self):
        return self._is_running

    def run(self):
        self._is_running = True

        try:
            log.info("Starting WebServer server")
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.start_server())

            asyncio.ensure_future(self.check_shutdown(), loop=self.loop)
            self.loop.run_forever()

        except Exception:
            log.warning(
                "Web Server service has failed", exc_info=True
            )
        finally:
            self.loop.close()

        self._is_running = False
        log.info("Web server stopped")

    async def start_server(self):
        """ Starts runner and TCPsite """
        self.runner = web.AppRunner(self.manager.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

    def stop(self):
        """Sets _stopped flag to True, 'check_shutdown' shuts server down"""
        self._stopped = True

    async def check_shutdown(self):
        """ Future that is running and checks if server should be running
            periodically.
        """
        while not self._stopped:
            await asyncio.sleep(0.5)

        print("Starting shutdown")
        if self.workers_route:
            await self.workers_route.stop()

        print("Stopping site")
        await self.site.stop()
        print("Site stopped")
        await self.runner.cleanup()

        print("Runner stopped")
        tasks = [
            task
            for task in asyncio.all_tasks()
            if task is not asyncio.current_task()
        ]
        list(map(lambda task: task.cancel(), tasks))  # cancel all the tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        log.debug(f'Finished awaiting cancelled tasks, results: {results}...')
        await self.loop.shutdown_asyncgens()
        # to really make sure everything else has time to stop
        await asyncio.sleep(0.07)
        self.loop.stop()
