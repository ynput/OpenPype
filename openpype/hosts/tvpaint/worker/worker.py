import os
import signal
import time
import tempfile
import shutil
import asyncio

from openpype.hosts.tvpaint.api.communication_server import (
    BaseCommunicator,
    CommunicationWrapper
)
from openpype_modules.job_queue.job_workers import WorkerJobsConnection

from .worker_job import ProcessTVPaintCommands


class TVPaintWorkerCommunicator(BaseCommunicator):
    """Modified commuicator which cares about processing jobs.

    Received jobs are send to TVPaint by parsing 'ProcessTVPaintCommands'.
    """
    def __init__(self, server_url):
        super().__init__()

        self.return_code = 1
        self._server_url = server_url
        self._worker_connection = None

    def _start_webserver(self):
        """Create connection to workers server before TVPaint server."""
        loop = self.websocket_server.loop
        self._worker_connection = WorkerJobsConnection(
            self._server_url, "tvpaint", loop
        )
        asyncio.ensure_future(
            self._worker_connection.main_loop(register_worker=False),
            loop=loop
        )

        super()._start_webserver()

    def _open_init_file(self):
        """Open init TVPaint file.

        File triggers dialog missing path to audio file which must be closed
        once and is ignored for rest of running process.
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        init_filepath = os.path.join(current_dir, "init_file.tvpp")
        with tempfile.NamedTemporaryFile(
            mode="w", prefix="a_tvp_", suffix=".tvpp"
        ) as tmp_file:
            tmp_filepath = tmp_file.name.replace("\\", "/")

        shutil.copy(init_filepath, tmp_filepath)
        george_script = "tv_LoadProject '\"'\"{}\"'\"'".format(tmp_filepath)
        self.execute_george_through_file(george_script)
        self.execute_george("tv_projectclose")
        os.remove(tmp_filepath)

    def _on_client_connect(self, *args, **kwargs):
        super()._on_client_connect(*args, **kwargs)
        self._open_init_file()
        # Register as "ready to work" worker
        self._worker_connection.register_as_worker()

    def stop(self):
        """Stop worker connection and TVPaint server."""
        self._worker_connection.stop()
        self.return_code = 0
        super().stop()

    @property
    def current_job(self):
        """Retrieve job which should be processed."""
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

        # Prepare variables used for sendig
        success = False
        message = "Unknown function"
        data = None
        job_data = job["data"]
        workfile = job_data["workfile"]
        # Currently can process only "commands" function
        if job_data.get("function") == "commands":
            try:
                commands = ProcessTVPaintCommands(
                    workfile, job_data["commands"], self
                )
                commands.execute()
                data = commands.response_data()
                success = True
                message = "Executed"

            except Exception as exc:
                message = "Error on worker: {}".format(str(exc))

        self._worker_connection.finish_job(success, message, data)

    def main_loop(self):
        """Main loop where jobs are processed.

        Server is stopped by killing this process or TVPaint process.
        """
        while self.server_is_running:
            if self._check_process():
                self._process_job()
            time.sleep(1)

        return self.return_code


def _start_tvpaint(tvpaint_executable_path, server_url):
    communicator = TVPaintWorkerCommunicator(server_url)
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
