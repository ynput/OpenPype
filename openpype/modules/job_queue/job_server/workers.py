import asyncio
from uuid import uuid4
from aiohttp import WSCloseCode
from aiohttp_json_rpc.protocol import encode_request


class WorkerState:
    IDLE = object()
    JOB_ASSIGNED = object()
    JOB_SENT = object()


class Worker:
    """Worker that can handle jobs of specific host."""
    def __init__(self, host_name, http_request):
        self._id = None
        self.host_name = host_name
        self._http_request = http_request
        self._state = WorkerState.IDLE
        self._job = None

        # Give ability to send requests to worker
        http_request.request_id = str(uuid4())
        http_request.pending_requests = {}

    async def send_job(self):
        if self._job is not None:
            data = {
                "job_id": self._job.id,
                "worker_id": self.id,
                "data": self._job.data
            }
            return await self.call("start_job", data)
        return False

    async def call(self, method, params=None, timeout=None):
        """Call method on worker's side."""
        request_id = self._http_request.request_id
        self._http_request.request_id = str(uuid4())
        pending_requests = self._http_request.pending_requests
        pending_requests[request_id] = asyncio.Future()

        request = encode_request(method, id=request_id, params=params)

        await self._http_request.ws.send_str(request)

        if timeout:
            await asyncio.wait_for(
                pending_requests[request_id],
                timeout=timeout
            )

        else:
            await pending_requests[request_id]

        result = pending_requests[request_id].result()
        del pending_requests[request_id]

        return result

    async def close(self):
        return await self.ws.close(
            code=WSCloseCode.GOING_AWAY,
            message="Server shutdown"
        )

    @property
    def id(self):
        if self._id is None:
            self._id = str(uuid4())
        return self._id

    @property
    def state(self):
        return self._state

    @property
    def current_job(self):
        return self._job

    @property
    def http_request(self):
        return self._http_request

    @property
    def ws(self):
        return self.http_request.ws

    def connection_is_alive(self):
        if self.ws.closed or self.ws._writer.transport.is_closing():
            return False
        return True

    def is_idle(self):
        return self._state is WorkerState.IDLE

    def job_assigned(self):
        return (
            self._state is WorkerState.JOB_ASSIGNED
            or self._state is WorkerState.JOB_SENT
        )

    def is_working(self):
        return self._state is WorkerState.JOB_SENT

    def set_current_job(self, job):
        if job is self._job:
            return

        self._job = job
        if job is None:
            self._set_idle()
        else:
            self._state = WorkerState.JOB_ASSIGNED
            job.set_worker(self)

    def _set_idle(self):
        self._job = None
        self._state = WorkerState.IDLE

    def set_working(self):
        self._state = WorkerState.JOB_SENT
