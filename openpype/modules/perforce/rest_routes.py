import os
import json
import datetime
import collections
import subprocess
from bson.objectid import ObjectId
from aiohttp.web_response import Response


from openpype.lib import Logger
from openpype.settings import get_project_settings
from openpype.modules.webserver.base_routes import RestApiEndpoint


log = Logger.get_logger("P4routes")


class P4ClientRestApiEndpoint(RestApiEndpoint):
    def __init__(self, p4_client):
        self.p4_client = p4_client
        super(P4ClientRestApiEndpoint, self).__init__()

    @staticmethod
    def json_dump_handler(value):
        if isinstance(value, datetime.datetime):
            return value.isoformat()
        if isinstance(value, ObjectId):
            return str(value)
        if isinstance(value, set):
            return list(value)
        raise TypeError(value)

    @classmethod
    def encode(cls, data):
        return json.dumps(
            data,
            indent=4,
            default=cls.json_dump_handler
        ).encode("utf-8")


class ChangesEndpoint(P4ClientRestApiEndpoint):
    """Returns list of dict with project info (id, name)."""
    async def get(self) -> Response:
        changeslist = self.p4_client.p4_run("changes", [])
        return Response(
            status=200,
            body=self.encode(changeslist),
            content_type="application/json"
        )


class CreateOrLoadOPChangelist(P4ClientRestApiEndpoint):
    """Returns list of dict with project info (id, name)."""
    async def post(self, request) -> Response:
        content = await request.json()

        result = self.p4_client.p4_create_or_load_openpype_changelist(
            **content)
        return Response(
            status=200,
            body=self.encode(result),
            content_type="application/json"
        )
