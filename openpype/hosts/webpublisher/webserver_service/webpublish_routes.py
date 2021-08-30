"""Routes and etc. for webpublisher API."""
import os
import json
import datetime
from bson.objectid import ObjectId
import collections
from aiohttp.web_response import Response
import subprocess

from avalon.api import AvalonMongoDB

from openpype.lib import OpenPypeMongoConnection
from openpype_modules.avalon_apps.rest_api import _RestApiEndpoint

from openpype.lib import PypeLogger

log = PypeLogger.get_logger("WebServer")


class RestApiResource:
    """Resource carrying needed info and Avalon DB connection for publish."""
    def __init__(self, server_manager, executable, upload_dir):
        self.server_manager = server_manager
        self.upload_dir = upload_dir
        self.executable = executable

        self.dbcon = AvalonMongoDB()
        self.dbcon.install()

    @staticmethod
    def json_dump_handler(value):
        if isinstance(value, datetime.datetime):
            return value.isoformat()
        if isinstance(value, ObjectId):
            return str(value)
        raise TypeError(value)

    @classmethod
    def encode(cls, data):
        return json.dumps(
            data,
            indent=4,
            default=cls.json_dump_handler
        ).encode("utf-8")


class OpenPypeRestApiResource(RestApiResource):
    """Resource carrying OP DB connection for storing batch info into DB."""
    def __init__(self, ):
        mongo_client = OpenPypeMongoConnection.get_mongo_client()
        database_name = os.environ["OPENPYPE_DATABASE_NAME"]
        self.dbcon = mongo_client[database_name]["webpublishes"]


class WebpublisherProjectsEndpoint(_RestApiEndpoint):
    """Returns list of dict with project info (id, name)."""
    async def get(self) -> Response:
        output = []
        for project_name in self.dbcon.database.collection_names():
            project_doc = self.dbcon.database[project_name].find_one({
                "type": "project"
            })
            if project_doc:
                ret_val = {
                    "id": project_doc["_id"],
                    "name": project_doc["name"]
                }
                output.append(ret_val)
        return Response(
            status=200,
            body=self.resource.encode(output),
            content_type="application/json"
        )


class WebpublisherHiearchyEndpoint(_RestApiEndpoint):
    """Returns dictionary with context tree from assets."""
    async def get(self, project_name) -> Response:
        query_projection = {
            "_id": 1,
            "data.tasks": 1,
            "data.visualParent": 1,
            "data.entityType": 1,
            "name": 1,
            "type": 1,
        }

        asset_docs = self.dbcon.database[project_name].find(
            {"type": "asset"},
            query_projection
        )
        asset_docs_by_id = {
            asset_doc["_id"]: asset_doc
            for asset_doc in asset_docs
        }

        asset_docs_by_parent_id = collections.defaultdict(list)
        for asset_doc in asset_docs_by_id.values():
            parent_id = asset_doc["data"].get("visualParent")
            asset_docs_by_parent_id[parent_id].append(asset_doc)

        assets = collections.defaultdict(list)

        for parent_id, children in asset_docs_by_parent_id.items():
            for child in children:
                node = assets.get(child["_id"])
                if not node:
                    node = Node(child["_id"],
                                child["data"].get("entityType", "Folder"),
                                child["name"])
                    assets[child["_id"]] = node

                    tasks = child["data"].get("tasks", {})
                    for t_name, t_con in tasks.items():
                        task_node = TaskNode("task", t_name)
                        task_node["attributes"]["type"] = t_con.get("type")

                        task_node.parent = node

                parent_node = assets.get(parent_id)
                if not parent_node:
                    asset_doc = asset_docs_by_id.get(parent_id)
                    if asset_doc:  # regular node
                        parent_node = Node(parent_id,
                                           asset_doc["data"].get("entityType",
                                                                 "Folder"),
                                           asset_doc["name"])
                    else:  # root
                        parent_node = Node(parent_id,
                                           "project",
                                           project_name)
                    assets[parent_id] = parent_node
                node.parent = parent_node

        roots = [x for x in assets.values() if x.parent is None]

        return Response(
            status=200,
            body=self.resource.encode(roots[0]),
            content_type="application/json"
        )


class Node(dict):
    """Node element in context tree."""

    def __init__(self, uid, node_type, name):
        self._parent = None  # pointer to parent Node
        self["type"] = node_type
        self["name"] = name
        self['id'] = uid  # keep reference to id #
        self['children'] = []  # collection of pointers to child Nodes

    @property
    def parent(self):
        return self._parent  # simply return the object at the _parent pointer

    @parent.setter
    def parent(self, node):
        self._parent = node
        # add this node to parent's list of children
        node['children'].append(self)


class TaskNode(Node):
    """Special node type only for Tasks."""

    def __init__(self, node_type, name):
        self._parent = None
        self["type"] = node_type
        self["name"] = name
        self["attributes"] = {}


class WebpublisherBatchPublishEndpoint(_RestApiEndpoint):
    """Triggers headless publishing of batch."""
    async def post(self, request) -> Response:
        output = {}
        log.info("WebpublisherBatchPublishEndpoint called")
        content = await request.json()

        batch_path = os.path.join(self.resource.upload_dir,
                                  content["batch"])

        openpype_app = self.resource.executable
        args = [
            openpype_app,
            'remotepublish',
            batch_path
        ]

        if not openpype_app or not os.path.exists(openpype_app):
            msg = "Non existent OpenPype executable {}".format(openpype_app)
            raise RuntimeError(msg)

        add_args = {
            "host": "webpublisher",
            "project": content["project_name"],
            "user": content["user"]
        }

        for key, value in add_args.items():
            args.append("--{}".format(key))
            args.append(value)

        log.info("args:: {}".format(args))

        subprocess.call(args)
        return Response(
            status=200,
            body=self.resource.encode(output),
            content_type="application/json"
        )


class WebpublisherTaskPublishEndpoint(_RestApiEndpoint):
    """Prepared endpoint triggered after each task - for future development."""
    async def post(self, request) -> Response:
        return Response(
            status=200,
            body=self.resource.encode([]),
            content_type="application/json"
        )


class BatchStatusEndpoint(_RestApiEndpoint):
    """Returns dict with info for batch_id."""
    async def get(self, batch_id) -> Response:
        output = self.dbcon.find_one({"batch_id": batch_id})

        return Response(
            status=200,
            body=self.resource.encode(output),
            content_type="application/json"
        )


class PublishesStatusEndpoint(_RestApiEndpoint):
    """Returns list of dict with batch info for user (email address)."""
    async def get(self, user) -> Response:
        output = list(self.dbcon.find({"user": user}))

        return Response(
            status=200,
            body=self.resource.encode(output),
            content_type="application/json"
        )
