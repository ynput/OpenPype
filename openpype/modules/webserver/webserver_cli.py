import attr
import time
import json
import datetime
from bson.objectid import ObjectId
import collections
from aiohttp.web_response import Response

from avalon.api import AvalonMongoDB
from openpype.modules.avalon_apps.rest_api import _RestApiEndpoint

from openpype.api import get_hierarchy


class WebpublisherProjectsEndpoint(_RestApiEndpoint):
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


@attr.s
class AssetItem(object):
    """Data class for Render Layer metadata."""
    id = attr.ib()
    name = attr.ib()

    # Render Products
    children = attr.ib(init=False, default=attr.Factory(list))


class WebpublisherHiearchyEndpoint(_RestApiEndpoint):
    async def get(self, project_name) -> Response:
        output = []
        query_projection = {
            "_id": 1,
            "data.tasks": 1,
            "data.visualParent": 1,
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

        asset_ids = list(asset_docs_by_id.keys())
        result = []
        if asset_ids:
            result = self.dbcon.database[project_name].aggregate([
                {
                    "$match": {
                        "type": "subset",
                        "parent": {"$in": asset_ids}
                    }
                },
                {
                    "$group": {
                        "_id": "$parent",
                        "count": {"$sum": 1}
                    }
                }
            ])

        asset_docs_by_parent_id = collections.defaultdict(list)
        for asset_doc in asset_docs_by_id.values():
            parent_id = asset_doc["data"].get("visualParent")
            asset_docs_by_parent_id[parent_id].append(asset_doc)

        appending_queue = collections.deque()
        appending_queue.append((None, "root"))

        asset_items_by_id = {}
        non_modifiable_items = set()
        assets = {}

        # # # while appending_queue:
        # # assets = self._recur_hiearchy(asset_docs_by_parent_id,
        # #                               appending_queue,
        # #                               assets, None)
        # while asset_docs_by_parent_id:
        #     for parent_id, asset_docs in asset_items_by_id.items():
        #         asset_docs = asset_docs_by_parent_id.get(parent_id) or []

        while appending_queue:
            parent_id, parent_item_name = appending_queue.popleft()

            asset_docs = asset_docs_by_parent_id.get(parent_id) or []

            asset_item = assets.get(parent_id)
            if not asset_item:
                asset_item = AssetItem(str(parent_id), parent_item_name)

            for asset_doc in sorted(asset_docs, key=lambda item: item["name"]):
                child_item = AssetItem(str(asset_doc["_id"]),
                                       asset_doc["name"])
                asset_item.children.append(child_item)
                if not asset_doc["data"]["tasks"]:
                    appending_queue.append((asset_doc["_id"],
                                            child_item.name))

                else:
                    asset_item = child_item
                    for task_name, _ in asset_doc["data"]["tasks"].items():
                        child_item = AssetItem(str(asset_doc["_id"]),
                                               task_name)
                        asset_item.children.append(child_item)
            assets[parent_id] = attr.asdict(asset_item)


        return Response(
            status=200,
            body=self.resource.encode(assets),
            content_type="application/json"
        )

    def _recur_hiearchy(self, asset_docs_by_parent_id,
                        appending_queue, assets, asset_item):
        parent_id, parent_item_name = appending_queue.popleft()

        asset_docs = asset_docs_by_parent_id.get(parent_id) or []

        if not asset_item:
            asset_item = assets.get(parent_id)
            if not asset_item:
                asset_item = AssetItem(str(parent_id), parent_item_name)

        for asset_doc in sorted(asset_docs, key=lambda item: item["name"]):
            child_item = AssetItem(str(asset_doc["_id"]),
                                   asset_doc["name"])
            asset_item.children.append(child_item)
            if not asset_doc["data"]["tasks"]:
                appending_queue.append((asset_doc["_id"],
                                        child_item.name))
                asset_item = child_item
                assets = self._recur_hiearchy(asset_docs_by_parent_id, appending_queue,
                                     assets, asset_item)
            else:
                asset_item = child_item
                for task_name, _ in asset_doc["data"]["tasks"].items():
                    child_item = AssetItem(str(asset_doc["_id"]),
                                           task_name)
                    asset_item.children.append(child_item)
        assets[asset_item.id] = attr.asdict(asset_item)

        return assets

class RestApiResource:
    def __init__(self, server_manager):
        self.server_manager = server_manager

        self.dbcon = AvalonMongoDB()
        self.dbcon.install()

    @staticmethod
    def json_dump_handler(value):
        print("valuetype:: {}".format(type(value)))
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


def run_webserver():
    print("webserver")
    from openpype.modules import ModulesManager

    manager = ModulesManager()
    webserver_module = manager.modules_by_name["webserver"]
    webserver_module.create_server_manager()

    resource = RestApiResource(webserver_module.server_manager)
    projects_endpoint = WebpublisherProjectsEndpoint(resource)
    webserver_module.server_manager.add_route(
        "GET",
        "/webpublisher/projects",
        projects_endpoint.dispatch
    )

    hiearchy_endpoint = WebpublisherHiearchyEndpoint(resource)
    webserver_module.server_manager.add_route(
        "GET",
        "/webpublisher/hiearchy/{project_name}",
        hiearchy_endpoint.dispatch
    )

    webserver_module.start_server()
    while True:
        time.sleep(0.5)

