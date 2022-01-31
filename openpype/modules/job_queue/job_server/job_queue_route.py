import json

from aiohttp.web_response import Response


class JobQueueResource:
    def __init__(self, job_queue, server_manager):
        self.server_manager = server_manager

        self._prefix = "/api"

        self._job_queue = job_queue

        self.endpoint_defs = (
            ("POST", "/jobs", self.post_job),
            ("GET", "/jobs", self.get_jobs),
            ("GET", "/jobs/{job_id}", self.get_job)
        )

        self.register()

    def register(self):
        for methods, url, callback in self.endpoint_defs:
            final_url = self._prefix + url
            self.server_manager.add_route(
                methods, final_url, callback
            )

    async def get_jobs(self, request):
        jobs_data = []
        for job in self._job_queue.get_jobs():
            jobs_data.append(job.status())
        return Response(status=200, body=self.encode(jobs_data))

    async def post_job(self, request):
        data = await request.json()
        host_name = data.get("host_name")
        if not host_name:
            return Response(
                status=400, message="Key \"host_name\" not filled."
            )

        job = self._job_queue.create_job(host_name, data)
        return Response(status=201, text=job.id)

    async def get_job(self, request):
        job_id = request.match_info["job_id"]
        content = self._job_queue.get_job_status(job_id)
        if content is None:
            content = {}
        return Response(
            status=200,
            body=self.encode(content),
            content_type="application/json"
        )

    @classmethod
    def encode(cls, data):
        return json.dumps(
            data,
            indent=4
        ).encode("utf-8")
