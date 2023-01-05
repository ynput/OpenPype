# -*- coding: utf-8 -*-
"""Collect scene data."""
import os

import pyblish.api
import openpype.hosts.harmony.api as harmony


class CollectScene(pyblish.api.ContextPlugin):
    """Collect basic scene information."""

    label = "Scene Data"
    order = pyblish.api.CollectorOrder
    hosts = ["harmony"]

    def process(self, context):
        """Plugin entry point."""
        result = harmony.send(
            {
                f"function": "PypeHarmony.getSceneSettings",
                "args": []}
        )["result"]

        context.data["applicationPath"] = result[0]
        context.data["scenePath"] = os.path.join(
            result[1], result[2] + ".xstage")
        context.data["frameRate"] = result[3]
        context.data["frameStartHandle"] = result[4]
        context.data["frameEndHandle"] = result[5]
        context.data["audioPath"] = result[6]
        context.data["resolutionWidth"] = result[7]
        context.data["resolutionHeight"] = result[8]
        context.data["FOV"] = result[9]

        # harmony always starts from 1. frame
        # 1001 - 10010 >> 1 - 10
        # frameStart, frameEnd already collected by global plugin
        offset = context.data["frameStart"] - 1
        frame_start = context.data["frameStart"] - offset
        frames_count = context.data["frameEnd"] - \
            context.data["frameStart"] + 1

        # increase by handleStart - real frame range
        # frameStart != frameStartHandle with handle presence
        context.data["frameStart"] = int(frame_start) + \
            context.data["handleStart"]
        context.data["frameEnd"] = int(frames_count) + \
            context.data["frameStart"] - 1

        all_nodes = harmony.send(
            {"function": "node.subNodes", "args": ["Top"]}
        )["result"]

        context.data["allNodes"] = all_nodes

        # collect all write nodes to be able disable them in Deadline
        all_write_nodes = harmony.send(
            {"function": "node.getNodes", "args": ["WRITE"]}
        )["result"]

        context.data["all_write_nodes"] = all_write_nodes

        result = harmony.send(
            {
                f"function": "PypeHarmony.getVersion",
                "args": []}
        )["result"]
        context.data["harmonyVersion"] = "{}.{}".format(result[0], result[1])
