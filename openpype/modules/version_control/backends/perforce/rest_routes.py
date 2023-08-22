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

from openpype.modules.version_control.backends.perforce.backend import (
    VersionControlPerforce
)


log = Logger.get_logger("P4routes")


class PerforceRestApiEndpoint(RestApiEndpoint):
    def __init__(self):
        super(PerforceRestApiEndpoint, self).__init__()

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


class AddEndpoint(PerforceRestApiEndpoint):
    """Returns list of dict with project info (id, name)."""
    async def post(self, request) -> Response:
        log.info("AddEndpoint called")
        content = await request.json()

        result = VersionControlPerforce.add(content["path"],
                                            content["comment"])
        return Response(
            status=200,
            body=self.encode(result),
            content_type="application/json"
        )


class CheckoutEndpoint(PerforceRestApiEndpoint):
    """Returns list of dict with project info (id, name)."""
    async def post(self, request) -> Response:
        log.info("CheckoutEndpoint called")

        content = await request.json()

        result = VersionControlPerforce.checkout(content["path"],
                                                 content["comment"])
        return Response(
            status=200,
            body=self.encode(result),
            content_type="application/json"
        )


class SubmitChangelist(PerforceRestApiEndpoint):
    """Returns list of dict with project info (id, name)."""
    async def post(self, request) -> Response:
        log.info("SubmitChangelist called")
        content = await request.json()

        result = VersionControlPerforce.submit_change_list(content["comment"])
        return Response(
            status=200,
            body=self.encode(result),
            content_type="application/json"
        )


class GetServerVersionEndpoint(PerforceRestApiEndpoint):
    """Returns list of dict with project info (id, name)."""
    async def get(self) -> Response:
        result = VersionControlPerforce.get_server_version()
        return Response(
            status=200,
            body=self.encode(result),
            content_type="application/json"
        )
