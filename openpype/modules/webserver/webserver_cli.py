import os
import time
import json
import datetime
from bson.objectid import ObjectId
import collections
from aiohttp.web_response import Response
import subprocess

from avalon.api import AvalonMongoDB

from openpype.lib import OpenPypeMongoConnection
from openpype.modules.avalon_apps.rest_api import _RestApiEndpoint


class WebpublisherProjectsEndpoint(_RestApiEndpoint):
    """Returns list of project names."""
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
                                child["data"]["entityType"],
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
                                           asset_doc["data"]["entityType"],
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


class WebpublisherPublishEndpoint(_RestApiEndpoint):
    """Returns list of project names."""
    async def post(self, request) -> Response:
        output = {}

        print(request)

        batch_path = os.path.join(self.resource.upload_dir,
                                  request.query["batch_id"])

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
            "project": request.query["project"],
            "user": request.query["user"]
        }

        for key, value in add_args.items():
            args.append("--{}".format(key))
            args.append(value)

        print("args:: {}".format(args))

        exit_code = subprocess.call(args, shell=True)
        return Response(
            status=200,
            body=self.resource.encode(output),
            content_type="application/json"
        )


class BatchStatusEndpoint(_RestApiEndpoint):
    """Returns list of project names."""
    async def get(self, batch_id) -> Response:
        output = self.dbcon.find_one({"batch_id": batch_id})

        return Response(
            status=200,
            body=self.resource.encode(output),
            content_type="application/json"
        )


class PublishesStatusEndpoint(_RestApiEndpoint):
    """Returns list of project names."""
    async def get(self, user) -> Response:
        output = self.dbcon.find({"user": user})

        return Response(
            status=200,
            body=self.resource.encode(output),
            content_type="application/json"
        )


class RestApiResource:
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
    def __init__(self, ):
        mongo_client = OpenPypeMongoConnection.get_mongo_client()
        database_name = os.environ["OPENPYPE_DATABASE_NAME"]
        self.dbcon = mongo_client[database_name]["webpublishes"]


def run_webserver(*args, **kwargs):
    from openpype.modules import ModulesManager

    manager = ModulesManager()
    webserver_module = manager.modules_by_name["webserver"]
    webserver_module.create_server_manager()

    resource = RestApiResource(webserver_module.server_manager,
                               upload_dir=kwargs["upload_dir"],
                               executable=kwargs["executable"])
    projects_endpoint = WebpublisherProjectsEndpoint(resource)
    webserver_module.server_manager.add_route(
        "GET",
        "/api/projects",
        projects_endpoint.dispatch
    )

    hiearchy_endpoint = WebpublisherHiearchyEndpoint(resource)
    webserver_module.server_manager.add_route(
        "GET",
        "/api/hierarchy/{project_name}",
        hiearchy_endpoint.dispatch
    )

    webpublisher_publish_endpoint = WebpublisherPublishEndpoint(resource)
    webserver_module.server_manager.add_route(
        "POST",
        "/api/webpublish/{batch_id}",
        webpublisher_publish_endpoint.dispatch
    )

    openpype_resource = OpenPypeRestApiResource()
    batch_status_endpoint = BatchStatusEndpoint(openpype_resource)
    webserver_module.server_manager.add_route(
        "GET",
        "/api/batch_status/{batch_id}",
        batch_status_endpoint.dispatch
    )

    user_status_endpoint = PublishesStatusEndpoint(openpype_resource)
    webserver_module.server_manager.add_route(
        "GET",
        "/api/publishes/{user}",
        user_status_endpoint.dispatch
    )

    webserver_module.start_server()
    while True:
        time.sleep(0.5)

