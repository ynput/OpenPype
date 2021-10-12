import signal
import time
import asyncio

from openpype.hosts.tvpaint.worker import TVPaintCommands
from avalon.tvpaint.communication_server import (
    BaseCommunicator,
    CommunicationWrapper
)
from .base_worker import WorkerJobsConnection


class WorkerCommunicator(BaseCommunicator):
    def __init__(self, server_url):
        super().__init__()

        self.return_code = 1
        self._server_url = server_url
        self._worker_connection = None

    def _start_webserver(self):
        loop = self.websocket_server.loop
        self._worker_connection = WorkerJobsConnection(
            self._server_url, "tvpaint", loop
        )
        asyncio.ensure_future(
            self._worker_connection.main_loop(register_worker=False),
            loop=loop
        )

        super()._start_webserver()

    def _on_client_connect(self, *args, **kwargs):
        super()._on_client_connect(*args, **kwargs)
        self._worker_connection.register_as_worker()

    def stop(self):
        self._worker_connection.stop()
        self.return_code = 0
        super().stop()

    @property
    def current_job(self):
        if self._worker_connection:
            return self._worker_connection.current_job
        return None

    def _check_process(self):
        if self.process is None:
            return True

        if self.process.poll() is not None:
            asyncio.ensure_future(
                self._worker_connection.disconnect(),
                loop=self.websocket_server.loop
            )
            self._exit()
            return False
        return True

    def _process_job(self):
        job = self.current_job
        if job is None:
            return

        success = False
        message = "Unknown function"
        data = None
        job_data = job["data"]
        workfile = job_data["workfile"]
        if job_data.get("function") == "commands":
            commands = TVPaintCommands(
                workfile, job_data["commands"], self
            )
            commands.execute()
            success = True
            message = "Executed"
            data = commands.result()

        self._worker_connection.finish_job(success, message, data)

    def main_loop(self):
        while self.server_is_running:
            if self._check_process():
                self._process_job()
            time.sleep(1)

        return self.return_code


def _start_tvpaint(tvpaint_executable_path, server_url):
    communicator = WorkerCommunicator(server_url)
    CommunicationWrapper.set_communicator(communicator)
    communicator.launch([tvpaint_executable_path])


def main(tvpaint_executable_path, server_url):
    # Register terminal signal handler
    def signal_handler(*_args):
        print("Termination signal received. Stopping.")
        if CommunicationWrapper.communicator is not None:
            CommunicationWrapper.communicator.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    _start_tvpaint(tvpaint_executable_path, server_url)

    communicator = CommunicationWrapper.communicator
    if communicator is None:
        print("Communicator is not set")
        return 1

    return communicator.main_loop()
