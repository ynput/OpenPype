# -*- coding: utf-8 -*-
"""Collect render data."""

import os
import re

import bpy

import pyblish.api


class CollectBlenderRender(pyblish.api.InstancePlugin):
    """Gather all publishable render layers from renderSetup."""

    order = pyblish.api.CollectorOrder + 0.01
    hosts = ["blender"]
    families = ["renderlayer"]
    label = "Collect Render Layers"
    sync_workfile_version = False

    def process(self, instance):
        context = instance.context

        filepath = context.data["currentFile"].replace("\\", "/")

        frame_start = context.data["frameStart"]
        frame_end = context.data["frameEnd"]
        frame_handle_start = context.data["frameStartHandle"]
        frame_handle_end = context.data["frameEndHandle"]

        instance.data.update({
            "frameStart": frame_start,
            "frameEnd": frame_end,
            "frameStartHandle": frame_handle_start,
            "frameEndHandle": frame_handle_end,
            "fps": context.data["fps"],
            "byFrameStep": bpy.context.scene.frame_step,
            "farm": True,
            "toBeRenderedOn": "deadline",
        })

        # instance.data["expectedFiles"] = self.generate_expected_files(
        #     instance, filepath)

        expected_files = []

        for frame in range(
            int(frame_start),
            int(frame_end) + 1,
            int(bpy.context.scene.frame_step),
        ):
            frame_str = str(frame).rjust(4, "0")
            expected_files.append(f"C:/tmp/{frame_str}.png")

        instance.data["expectedFiles"] = expected_files

        self.log.debug(instance.data["expectedFiles"])

    def generate_expected_files(self, instance, path):
        """Create expected files in instance data"""

        dir = os.path.dirname(path)
        file = os.path.basename(path)

        if "#" in file:
            def replace(match):
                return "%0{}d".format(len(match.group()))

            file = re.sub("#+", replace, file)

        if "%" not in file:
            return path

        expected_files = []
        start = instance.data["frameStart"]
        end = instance.data["frameEnd"]
        for i in range(int(start), (int(end) + 1)):
            expected_files.append(
                os.path.join(dir, (file % i)).replace("\\", "/"))

        return expected_files
