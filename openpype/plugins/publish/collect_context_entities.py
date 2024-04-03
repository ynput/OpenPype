"""Collect Anatomy and global anatomy data.

Requires:
    session -> AVALON_ASSET
    context -> projectName
    context -> asset
    context -> task

Provides:
    context -> projectEntity - Project document from database.
    context -> assetEntity - Asset document from database only if 'asset' is
        set in context.
"""

import pyblish.api

from openpype.client import get_project, get_asset_by_name
from openpype.pipeline import KnownPublishError


class CollectContextEntities(pyblish.api.ContextPlugin):
    """Collect entities into Context."""

    order = pyblish.api.CollectorOrder - 0.1
    label = "Collect Context Entities"

    def process(self, context):
        project_name = context.data["projectName"]
        asset_name = context.data["asset"]
        task_name = context.data["task"]

        project_entity = get_project(project_name)
        if not project_entity:
            raise KnownPublishError(
                "Project '{0}' was not found.".format(project_name)
            )
        self.log.debug("Collected Project \"{}\"".format(project_entity))

        context.data["projectEntity"] = project_entity

        if not asset_name:
            self.log.info("Context is not set. Can't collect global data.")
            return

        asset_entity = get_asset_by_name(project_name, asset_name)
        assert asset_entity, (
            "No asset found by the name '{0}' in project '{1}'"
        ).format(asset_name, project_name)

        self.log.debug("Collected Asset \"{}\"".format(asset_entity))

        context.data["assetEntity"] = asset_entity

        data = asset_entity['data']

        # Task type
        asset_tasks = data.get("tasks") or {}
        task_info = asset_tasks.get(task_name) or {}
        task_custom_atr = task_info.get("custom_attributes") or {}
        task_frame_start = task_custom_atr.get("frameStart")
        task_frame_end = task_custom_atr.get("frameEnd")
        task_handle_start = task_custom_atr.get("handleStart")
        task_handle_end = task_custom_atr.get("handleEnd")

        task_type = task_info.get("type")
        context.data["taskType"] = task_type

        frame_start = data.get("frameStart")
        if task_frame_start is not None:
            frame_start = int(task_frame_start)

        if frame_start is None:
            frame_start = 1
            self.log.warning("Missing frame start. Defaulting to 1.")

        frame_end = data.get("frameEnd")
        if task_frame_end is not None:
            frame_end = int(task_frame_end)

        if frame_end is None:
            frame_end = 2
            self.log.warning("Missing frame end. Defaulting to 2.")

        context.data["frameStart"] = frame_start
        context.data["frameEnd"] = frame_end

        handle_start = data.get("handleStart") or 0
        if task_handle_start is not None:
            handle_start = int(task_handle_start)

        handle_end = data.get("handleEnd") or 0
        if task_handle_end is not None:
            handle_end = int(task_handle_end)

        context.data["handleStart"] = int(handle_start)
        context.data["handleEnd"] = int(handle_end)

        frame_start_h = frame_start - context.data["handleStart"]
        frame_end_h = frame_end + context.data["handleEnd"]
        context.data["frameStartHandle"] = frame_start_h
        context.data["frameEndHandle"] = frame_end_h

        context.data["fps"] = data["fps"]

        if "tools_env" not in data:
            data["tools_env"] = []

        context.data["tools_env"] = data["tools_env"]
