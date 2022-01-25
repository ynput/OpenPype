import sys
import datetime
import asyncio
import traceback

from aiohttp_json_rpc import JsonRpcClient


class WorkerClient(JsonRpcClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.add_methods(
            ("", self.start_job),
        )
        self.current_job = None
        self._id = None

    def set_id(self, worker_id):
        self._id = worker_id

    async def start_job(self, job_data):
        if self.current_job is not None:
            return False

        print("Got new job {}".format(str(job_data)))
        self.current_job = job_data
        return True

    def finish_job(self, success, message, data):
        asyncio.ensure_future(
            self._finish_job(success, message, data),
            loop=self._loop
        )

    async def _finish_job(self, success, message, data):
        print("Current job", self.current_job)
        job_id = self.current_job["job_id"]
        self.current_job = None

        return await self.call(
            "job_done", [self._id, job_id, success, message, data]
        )


class WorkerJobsConnection:
    """WS connection to Job server.

    Helper class to create a connection to process jobs from job server.

    To be able receive jobs is needed to create a connection and then register
    as worker for specific host.
    """
    retry_time_seconds = 5

    def __init__(self, server_url, host_name, loop=None):
        self.client = None
        self._loop = loop

        self._host_name = host_name
        self._server_url = server_url

        self._is_running = False
        self._connecting = False
        self._connected = False
        self._stopped = False

    def stop(self):
        print("Stopping worker")
        self._stopped = True

    @property
    def is_running(self):
        return self._is_running

    @property
    def current_job(self):
        if self.client is not None:
            return self.client.current_job
        return None

    def finish_job(self, success=True, message=None, data=None):
        """Worker finished job and sets the result which is send to server."""
        if self.client is None:
            print((
                "Couldn't sent job status to server because"
                " client is not connected."
            ))
        else:
            self.client.finish_job(success, message, data)

    async def main_loop(self, register_worker=True):
        """Main loop of connection which keep connection to server alive."""
        self._is_running = True

        while not self._stopped:
            start_time = datetime.datetime.now()
            await self._connection_loop(register_worker)
            delta = datetime.datetime.now() - start_time
            print("Connection loop took {}s".format(str(delta)))
            # Check if was stopped and stop while loop in that case
            if self._stopped:
                break

            if delta.seconds < 60:
                print((
                    "Can't connect to server will try in {} seconds."
                ).format(self.retry_time_seconds))

                await asyncio.sleep(self.retry_time_seconds)
        self._is_running = False

    async def _connect(self):
        self.client = WorkerClient()
        print("Connecting to {}".format(self._server_url))
        try:
            await self.client.connect_url(self._server_url)
        except KeyboardInterrupt:
            raise
        except Exception:
            traceback.print_exception(*sys.exc_info())

    async def _connection_loop(self, register_worker):
        self._connecting = True
        future = asyncio.run_coroutine_threadsafe(
            self._connect(), loop=self._loop
        )

        while self._connecting:
            if not future.done():
                await asyncio.sleep(0.07)
                continue

            session = getattr(self.client, "_session", None)
            ws = getattr(self.client, "_ws", None)
            if session is not None:
                if session.closed:
                    self._connecting = False
                    self._connected = False
                    break

                elif ws is not None:
                    self._connecting = False
                    self._connected = True

            if self._stopped:
                break

            await asyncio.sleep(0.07)

        if not self._connected:
            self.client = None
            return

        print("Connected to job queue server")
        if register_worker:
            self.register_as_worker()

        while self._connected and self._loop.is_running():
            if self._stopped or ws.closed:
                break

            await asyncio.sleep(0.3)

        await self._stop_cleanup()

    def register_as_worker(self):
        """Register as worker ready to work on server side."""
        asyncio.ensure_future(self._register_as_worker(), loop=self._loop)

    async def _register_as_worker(self):
        worker_id = await self.client.call(
            "register_worker", [self._host_name]
        )
        self.client.set_id(worker_id)
        print(
            "Registered as worker with id {}".format(worker_id)
        )

    async def disconnect(self):
        await self._stop_cleanup()

    async def _stop_cleanup(self):
        print("Cleanup after stop")
        if self.client is not None and hasattr(self.client, "_ws"):
            await self.client.disconnect()

        self.client = None
        self._connecting = False
        self._connected = False
