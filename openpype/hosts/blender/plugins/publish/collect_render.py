# -*- coding: utf-8 -*-
"""Collect render data."""

import os
import re

import bpy

from openpype.hosts.blender.api import colorspace
import pyblish.api


class CollectBlenderRender(pyblish.api.InstancePlugin):
    """Gather all publishable render instances."""

    order = pyblish.api.CollectorOrder + 0.01
    hosts = ["blender"]
    families = ["render"]
    label = "Collect Render"
    sync_workfile_version = False

    @staticmethod
    def generate_expected_beauty(
        render_product, frame_start, frame_end, frame_step, ext
    ):
        """
        Generate the expected files for the render product for the beauty
        render. This returns a list of files that should be rendered. It
        replaces the sequence of `#` with the frame number.
        """
        path = os.path.dirname(render_product)
        file = os.path.basename(render_product)

        expected_files = []

        for frame in range(frame_start, frame_end + 1, frame_step):
            frame_str = str(frame).rjust(4, "0")
            filename = re.sub("#+", frame_str, file)
            expected_file = f"{os.path.join(path, filename)}.{ext}"
            expected_files.append(expected_file.replace("\\", "/"))

        return {
            "beauty": expected_files
        }

    @staticmethod
    def generate_expected_aovs(
        aov_file_product, frame_start, frame_end, frame_step, ext
    ):
        """
        Generate the expected files for the render product for the beauty
        render. This returns a list of files that should be rendered. It
        replaces the sequence of `#` with the frame number.
        """
        expected_files = {}

        for aov_name, aov_file in aov_file_product:
            path = os.path.dirname(aov_file)
            file = os.path.basename(aov_file)

            aov_files = []

            for frame in range(frame_start, frame_end + 1, frame_step):
                frame_str = str(frame).rjust(4, "0")
                filename = re.sub("#+", frame_str, file)
                expected_file = f"{os.path.join(path, filename)}.{ext}"
                aov_files.append(expected_file.replace("\\", "/"))

            expected_files[aov_name] = aov_files

        return expected_files

    def process(self, instance):
        context = instance.context

        instance_node = instance.data["transientData"]["instance_node"]
        render_data = instance_node.get("render_data")

        assert render_data, "No render data found."

        render_product = render_data.get("render_product")
        aov_file_product = render_data.get("aov_file_product")
        ext = render_data.get("image_format")
        multilayer = render_data.get("multilayer_exr")

        frame_start = context.data["frameStart"]
        frame_end = context.data["frameEnd"]
        frame_handle_start = context.data["frameStartHandle"]
        frame_handle_end = context.data["frameEndHandle"]

        expected_beauty = self.generate_expected_beauty(
            render_product, int(frame_start), int(frame_end),
            int(bpy.context.scene.frame_step), ext)

        expected_aovs = self.generate_expected_aovs(
            aov_file_product, int(frame_start), int(frame_end),
            int(bpy.context.scene.frame_step), ext)

        expected_files = expected_beauty | expected_aovs

        instance.data.update({
            "families": ["render", "render.farm"],
            "frameStart": frame_start,
            "frameEnd": frame_end,
            "frameStartHandle": frame_handle_start,
            "frameEndHandle": frame_handle_end,
            "fps": context.data["fps"],
            "byFrameStep": bpy.context.scene.frame_step,
            "review": render_data.get("review", False),
            "multipartExr": ext == "exr" and multilayer,
            "farm": True,
            "expectedFiles": [expected_files],
            # OCIO not currently implemented in Blender, but the following
            # settings are required by the schema, so it is hardcoded.
            # TODO: Implement OCIO in Blender
            "colorspaceConfig": "",
            "colorspaceDisplay": "sRGB",
            "colorspaceView": "ACES 1.0 SDR-video",
            "renderProducts": colorspace.ARenderProduct(),
        })
