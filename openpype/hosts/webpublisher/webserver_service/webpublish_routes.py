"""Routes and etc. for webpublisher API."""
import os
import json
import datetime
from bson.objectid import ObjectId
import collections
from aiohttp.web_response import Response
import subprocess

from openpype.lib import (
    OpenPypeMongoConnection,
    PypeLogger,
)
from openpype.lib.remote_publish import (
    get_task_data,
    ERROR_STATUS,
    REPROCESS_STATUS
)
from openpype.pipeline import AvalonMongoDB
from openpype_modules.avalon_apps.rest_api import _RestApiEndpoint
from openpype.settings import get_project_settings



log = PypeLogger.get_logger("WebServer")


class RestApiResource:
    """Resource carrying needed info and Avalon DB connection for publish."""
    def __init__(self, server_manager, executable, upload_dir,
                 studio_task_queue=None):
        self.server_manager = server_manager
        self.upload_dir = upload_dir
        self.executable = executable

        if studio_task_queue is None:
            studio_task_queue = collections.deque().dequeu
        self.studio_task_queue = studio_task_queue

        self.dbcon = AvalonMongoDB()
        self.dbcon.install()

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


class OpenPypeRestApiResource(RestApiResource):
    """Resource carrying OP DB connection for storing batch info into DB."""
    def __init__(self, ):
        mongo_client = OpenPypeMongoConnection.get_mongo_client()
        database_name = os.environ["OPENPYPE_DATABASE_NAME"]
        self.dbcon = mongo_client[database_name]["webpublishes"]


class ProjectsEndpoint(_RestApiEndpoint):
    """Returns list of dict with project info (id, name)."""
    async def get(self) -> Response:
        output = []
        for project_doc in self.dbcon.projects():
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


class HiearchyEndpoint(_RestApiEndpoint):
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


class BatchPublishEndpoint(_RestApiEndpoint):
    """Triggers headless publishing of batch."""
    async def post(self, request) -> Response:
        # Validate existence of openpype executable
        openpype_app = self.resource.executable
        if not openpype_app or not os.path.exists(openpype_app):
            msg = "Non existent OpenPype executable {}".format(openpype_app)
            raise RuntimeError(msg)

        log.info("BatchPublishEndpoint called")
        content = await request.json()

        # Each filter have extensions which are checked on first task item
        #   - first filter with extensions that are on first task is used
        #   - filter defines command and can extend arguments dictionary
        # This is used only if 'studio_processing' is enabled on batch
        studio_processing_filters = [
            # TVPaint filter
            {
                "extensions": [".tvpp"],
                "command": "remotepublish",
                "arguments": {
                    "targets": ["tvpaint_worker"]
                },
                "add_to_queue": False
            },
            # Photoshop filter
            {
                "extensions": [".psd", ".psb"],
                "command": "remotepublishfromapp",
                "arguments": {
                    # Command 'remotepublishfromapp' requires --host argument
                    "host": "photoshop",
                    # Make sure targets are set to None for cases that default
                    #   would change
                    # - targets argument is not used in 'remotepublishfromapp'
                    "targets": ["remotepublish"]
                },
                # does publish need to be handled by a queue, eg. only
                # single process running concurrently?
                "add_to_queue": True
            }
        ]

        batch_dir = os.path.join(self.resource.upload_dir, content["batch"])

        # Default command and arguments
        command = "remotepublish"
        add_args = {
            # All commands need 'project' and 'user'
            "project": content["project_name"],
            "user": content["user"],

            "targets": ["filespublish"]
        }

        add_to_queue = False
        if content.get("studio_processing"):
            log.info("Post processing called for {}".format(batch_dir))

            task_data = get_task_data(batch_dir)

            for process_filter in studio_processing_filters:
                filter_extensions = process_filter.get("extensions") or []
                for file_name in task_data["files"]:
                    file_ext = os.path.splitext(file_name)[-1].lower()
                    if file_ext in filter_extensions:
                        # Change command
                        command = process_filter["command"]
                        # Update arguments
                        add_args.update(
                            process_filter.get("arguments") or {}
                        )
                        add_to_queue = process_filter["add_to_queue"]
                        break

        args = [
            openpype_app,
            command,
            batch_dir
        ]

        for key, value in add_args.items():
            # Skip key values where value is None
            if value is not None:
                args.append("--{}".format(key))
                # Extend list into arguments (targets can be a list)
                if isinstance(value, (tuple, list)):
                    args.extend(value)
                else:
                    args.append(value)

        log.info("args:: {}".format(args))
        if add_to_queue:
            log.debug("Adding to queue")
            self.resource.studio_task_queue.append(args)
        else:
            subprocess.call(args)

        return Response(
            status=200,
            content_type="application/json"
        )


class TaskPublishEndpoint(_RestApiEndpoint):
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

        if output:
            status = 200
        else:
            output = {"msg": "Batch id {} not found".format(batch_id),
                      "status": "queued",
                      "progress": 0}
            status = 404
        body = self.resource.encode(output)
        return Response(
            status=status,
            body=body,
            content_type="application/json"
        )


class UserReportEndpoint(_RestApiEndpoint):
    """Returns list of dict with batch info for user (email address)."""
    async def get(self, user) -> Response:
        output = list(self.dbcon.find({"user": user},
                                      projection={"log": False}))

        if output:
            status = 200
        else:
            output = {"msg": "User {} not found".format(user)}
            status = 404
        body = self.resource.encode(output)

        return Response(
            status=status,
            body=body,
            content_type="application/json"
        )


class ConfiguredExtensionsEndpoint(_RestApiEndpoint):
    """Returns dict of extensions which have mapping to family.

        Returns:
        {
            "file_exts": [],
            "sequence_exts": []
        }
    """
    async def get(self, project_name=None) -> Response:
        sett = get_project_settings(project_name)

        configured = {
            "file_exts": set(),
            "sequence_exts": set(),
            # workfiles that could have "Studio Processing" hardcoded for now
            "studio_exts": set(["psd", "psb", "tvpp", "tvp"])
        }
        collect_conf = sett["webpublisher"]["publish"]["CollectPublishedFiles"]
        configs = collect_conf.get("task_type_to_family", [])
        mappings = []
        for _, conf_mappings in configs.items():
            if isinstance(conf_mappings, dict):
                conf_mappings = conf_mappings.values()
            for conf_mapping in conf_mappings:
                mappings.append(conf_mapping)

        for mapping in mappings:
            if mapping["is_sequence"]:
                configured["sequence_exts"].update(mapping["extensions"])
            else:
                configured["file_exts"].update(mapping["extensions"])

        return Response(
            status=200,
            body=self.resource.encode(dict(configured)),
            content_type="application/json"
        )


class BatchReprocessEndpoint(_RestApiEndpoint):
    """Marks latest 'batch_id' for reprocessing, returns 404 if not found."""
    async def post(self, batch_id) -> Response:
        batches = self.dbcon.find({"batch_id": batch_id,
                                   "status": ERROR_STATUS}).sort("_id", -1)

        if batches:
            self.dbcon.update_one(
                {"_id": batches[0]["_id"]},
                {"$set": {"status": REPROCESS_STATUS}}
            )
            output = [{"msg": "Batch id {} set to reprocess".format(batch_id)}]
            status = 200
        else:
            output = [{"msg": "Batch id {} not found".format(batch_id)}]
            status = 404
        body = self.resource.encode(output)

        return Response(
            status=status,
            body=body,
            content_type="application/json"
        )
