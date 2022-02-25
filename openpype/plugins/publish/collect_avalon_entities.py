"""Collect Anatomy and global anatomy data.

Requires:
    session -> AVALON_PROJECT, AVALON_ASSET

Provides:
    context -> projectEntity - project entity from database
    context -> assetEntity - asset entity from database
"""

from avalon import io, api
import pyblish.api
from openpype.lib import get_frame_info, UnifiedFrameInfo


class CollectAvalonEntities(pyblish.api.ContextPlugin):
    """Collect Anatomy into Context"""

    order = pyblish.api.CollectorOrder - 0.1
    label = "Collect Avalon Entities"

    def process(self, context):
        io.install()
        project_name = api.Session["AVALON_PROJECT"]
        asset_name = api.Session["AVALON_ASSET"]
        task_name = api.Session["AVALON_TASK"]

        project_entity = io.find_one({
            "type": "project",
            "name": project_name
        })
        assert project_entity, (
            "Project '{0}' was not found."
        ).format(project_name)
        self.log.debug("Collected Project \"{}\"".format(project_entity))

        context.data["projectEntity"] = project_entity

        if not asset_name:
            self.log.info("Context is not set. Can't collect global data.")
            return
        asset_entity = io.find_one({
            "type": "asset",
            "name": asset_name,
            "parent": project_entity["_id"]
        })
        assert asset_entity, (
            "No asset found by the name '{0}' in project '{1}'"
        ).format(asset_name, project_name)

        self.log.debug("Collected Asset \"{}\"".format(asset_entity))

        context.data["assetEntity"] = asset_entity
        anatomy = context.data["anatomy"]
        context.data["assetFrameInfo"] = get_frame_info(
            asset_entity, anatomy=anatomy
        )

        data = asset_entity['data']

        # Task type
        asset_tasks = data.get("tasks") or {}
        task_info = asset_tasks.get(task_name) or {}
        task_type = task_info.get("type")
        context.data["taskType"] = task_type

        anatomy = context.data["anatomy"]

        frame_info = get_frame_info(asset_entity, anatomy)
        if frame_info is None:
            frame_info = UnifiedFrameInfo(1, 2, 0, 0)
            self.log.warning(
                "Missing frame information on asset. Using default 1-2 frames."
            )

        context.data["frameStart"] = frame_info.frame_start
        context.data["frameEnd"] = frame_info.frame_end

        context.data["handleStart"] = frame_info.handle_start
        context.data["handleEnd"] = frame_info.handle_end

        context.data["frameStartHandle"] = frame_info.handle_frame_start
        context.data["frameEndHandle"] = frame_info.handle_frame_end

        context.data["fps"] = data["fps"]
