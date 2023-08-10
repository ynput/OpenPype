# -*- coding: utf-8 -*-
"""Collect render data."""

import os
import re

import bpy

from openpype.pipeline import (
    get_current_project_name,
)
from openpype.settings import (
    get_project_settings,
)
import pyblish.api


class CollectBlenderRender(pyblish.api.InstancePlugin):
    """Gather all publishable render layers from renderSetup."""

    order = pyblish.api.CollectorOrder + 0.01
    hosts = ["blender"]
    families = ["renderlayer"]
    label = "Collect Render Layers"
    sync_workfile_version = False

    @staticmethod
    def get_default_render_folder(settings):
        """Get default render folder from blender settings."""

        return (settings["blender"]
                        ["RenderSettings"]
                        ["default_render_image_folder"])

    @staticmethod
    def get_image_format(settings):
        """Get image format from blender settings."""

        return (settings["blender"]
                        ["RenderSettings"]
                        ["image_format"])

    @staticmethod
    def get_render_product(file_path, render_folder, file_name, instance, ext):
        output_file = os.path.join(
            file_path, render_folder, file_name, instance.name)

        render_product = f"{output_file}.####.{ext}"
        render_product = render_product.replace("\\", "/")

        return render_product

    @staticmethod
    def generate_expected_files(
        render_product, frame_start, frame_end, frame_step
    ):
        path = os.path.dirname(render_product)
        file = os.path.basename(render_product)

        expected_files = []

        for frame in range(frame_start, frame_end + 1, frame_step):
            frame_str = str(frame).rjust(4, "0")
            expected_file = os.path.join(path, re.sub("#+", frame_str, file))
            expected_files.append(expected_file.replace("\\", "/"))

        return expected_files

    @staticmethod
    def set_render_format(ext):
        image_settings = bpy.context.scene.render.image_settings

        if ext == "exr":
            image_settings.file_format = "OPEN_EXR"
        elif ext == "bmp":
            image_settings.file_format = "BMP"
        elif ext == "iris":
            image_settings.file_format = "IRIS"
        elif ext == "png":
            image_settings.file_format = "PNG"
        elif ext == "jpeg":
            image_settings.file_format = "JPEG"
        elif ext == "jpeg2000":
            image_settings.file_format = "JPEG2000"
        elif ext == "tga":
            image_settings.file_format = "TARGA"
        elif ext == "tga_raw":
            image_settings.file_format = "TARGA_RAW"
        elif ext == "tiff":
            image_settings.file_format = "TIFF"

    @staticmethod
    def set_render_camera(instance):
        # There should be only one camera in the instance
        found = False
        for obj in instance:
            if isinstance(obj, bpy.types.Object) and obj.type == "CAMERA":
                bpy.context.scene.camera = obj
                found = True
                break

        assert found, "No camera found in the render instance"

    def process(self, instance):
        context = instance.context

        filepath = context.data["currentFile"].replace("\\", "/")
        file_path = os.path.dirname(filepath)
        file_name = os.path.basename(filepath)
        file_name, _ = os.path.splitext(file_name)

        project = get_current_project_name()
        settings = get_project_settings(project)

        render_folder = self.get_default_render_folder(settings)
        ext = self.get_image_format(settings)

        render_product = self.get_render_product(
            file_path, render_folder, file_name, instance, ext)

        # We set the render path, the format and the camera
        bpy.context.scene.render.filepath = render_product
        self.set_render_format(ext)
        self.set_render_camera(instance)

        # We save the file to save the render settings
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)

        frame_start = context.data["frameStart"]
        frame_end = context.data["frameEnd"]
        frame_handle_start = context.data["frameStartHandle"]
        frame_handle_end = context.data["frameEndHandle"]

        expected_files = self.generate_expected_files(
            render_product, int(frame_start), int(frame_end),
            int(bpy.context.scene.frame_step))

        instance.data.update({
            "frameStart": frame_start,
            "frameEnd": frame_end,
            "frameStartHandle": frame_handle_start,
            "frameEndHandle": frame_handle_end,
            "fps": context.data["fps"],
            "byFrameStep": bpy.context.scene.frame_step,
            "farm": True,
            "expectedFiles": expected_files,
        })

        self.log.info(f"data: {instance.data}")
