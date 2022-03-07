import asyncio

import aiohttp
from aiohttp_json_rpc import JsonRpc
from aiohttp_json_rpc.protocol import (
    encode_error, decode_msg, JsonRpcMsgTyp
)
from aiohttp_json_rpc.exceptions import RpcError
from .workers import Worker


class WorkerRpc(JsonRpc):
    def __init__(self, job_queue, manager, **kwargs):
        super().__init__(**kwargs)

        self._job_queue = job_queue
        self._manager = manager

        self._stopped = False

        # Register methods
        self.add_methods(
            ("", self.register_worker),
            ("", self.job_done)
        )
        asyncio.ensure_future(self._rpc_loop(), loop=self.loop)

        self._manager.add_route(
            "*", "/ws", self.handle_request
        )

    # Panel routes for tools
    async def register_worker(self, request, host_name):
        worker = Worker(host_name, request.http_request)
        self._job_queue.add_worker(worker)
        return worker.id

    async def _rpc_loop(self):
        while self.loop.is_running():
            if self._stopped:
                break

            for worker in tuple(self._job_queue.workers()):
                if not worker.connection_is_alive():
                    self._job_queue.remove_worker(worker)
            self._job_queue.assign_jobs()

            await self.send_jobs()
            await asyncio.sleep(5)

    async def job_done(self, worker_id, job_id, success, message, data):
        worker = self._job_queue.get_worker(worker_id)
        if worker is not None:
            worker.set_current_job(None)

        job = self._job_queue.get_job(job_id)
        if job is not None:
            job.set_done(success, message, data)
        return True

    async def send_jobs(self):
        invalid_workers = []
        for worker in self._job_queue.workers():
            if worker.job_assigned() and not worker.is_working():
                try:
                    await worker.send_job()

                except ConnectionResetError:
                    invalid_workers.append(worker)

        for worker in invalid_workers:
            self._job_queue.remove_worker(worker)

    async def handle_websocket_request(self, http_request):
        """Override this method to catch CLOSING messages."""
        http_request.msg_id = 0
        http_request.pending = {}

        # prepare and register websocket
        ws = aiohttp.web_ws.WebSocketResponse()
        await ws.prepare(http_request)
        http_request.ws = ws
        self.clients.append(http_request)

        while not ws.closed:
            self.logger.debug('waiting for messages')
            raw_msg = await ws.receive()

            if raw_msg.type == aiohttp.WSMsgType.TEXT:
                self.logger.debug('raw msg received: %s', raw_msg.data)
                self.loop.create_task(
                    self._handle_rpc_msg(http_request, raw_msg)
                )

            elif raw_msg.type == aiohttp.WSMsgType.CLOSING:
                break

        self.clients.remove(http_request)
        return ws

    async def _handle_rpc_msg(self, http_request, raw_msg):
        # This is duplicated code from super but there is no way how to do it
        # to be able handle server->client requests
        try:
            _raw_message = raw_msg.data
            msg = decode_msg(_raw_message)

        except RpcError as error:
            await self._ws_send_str(http_request, encode_error(error))
            return

        if msg.type in (JsonRpcMsgTyp.RESULT, JsonRpcMsgTyp.ERROR):
            request_id = msg.data["id"]
            if request_id in http_request.pending_requests:
                future = http_request.pending_requests[request_id]
                future.set_result(msg.data["result"])
                return

        return await super()._handle_rpc_msg(http_request, raw_msg)

    async def stop(self):
        self._stopped = True
        for worker in tuple(self._job_queue.workers()):
            await worker.close()
