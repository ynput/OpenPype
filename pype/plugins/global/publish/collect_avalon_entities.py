"""Collect Anatomy and global anatomy data.

Requires:
    session -> AVALON_PROJECT, AVALON_ASSET

Provides:
    context -> projectEntity - project entity from database
    context -> assetEntity - asset entity from database
"""

from avalon import io, api
import pyblish.api


class CollectAvalonEntities(pyblish.api.ContextPlugin):
    """Collect Anatomy into Context"""

    order = pyblish.api.CollectorOrder - 0.02
    label = "Collect Avalon Entities"

    def process(self, context):
        io.install()
        project_name = api.Session["AVALON_PROJECT"]
        asset_name = api.Session["AVALON_ASSET"]

        project_entity = io.find_one({
            "type": "project",
            "name": project_name
        })
        assert project_entity, (
            "Project '{0}' was not found."
        ).format(project_name)
        self.log.debug("Collected Project \"{}\"".format(project_entity))

        asset_entity = io.find_one({
            "type": "asset",
            "name": asset_name,
            "parent": project_entity["_id"]
        })
        assert asset_entity, (
            "No asset found by the name '{0}' in project '{1}'"
        ).format(asset_name, project_name)

        self.log.debug("Collected Asset \"{}\"".format(asset_entity))

        context.data["projectEntity"] = project_entity
        context.data["assetEntity"] = asset_entity

        data = asset_entity['data']

        context.data["frameStart"] = data.get("frameStart")
        context.data["frameEnd"] = data.get("frameEnd")

        handles = int(data.get("handles") or 0)
        context.data["handles"] = handles
        context.data["handleStart"] = int(data.get("handleStart", handles))
        context.data["handleEnd"] = int(data.get("handleEnd", handles))

        frame_start_h = data.get("frameStart") - context.data["handleStart"]
        frame_end_h = data.get("frameEnd") + context.data["handleEnd"]
        context.data["frameStartHandle"] = frame_start_h
        context.data["frameEndHandle"] = frame_end_h
