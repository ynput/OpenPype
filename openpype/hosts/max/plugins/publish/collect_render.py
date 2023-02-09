# -*- coding: utf-8 -*-
"""Collect Render"""
import os
import pyblish.api

from pymxs import runtime as rt
from openpype.pipeline import legacy_io
from openpype.hosts.max.api.lib import get_current_renderer
from openpype.hosts.max.api.lib_renderproducts import RenderProducts


class CollectRender(pyblish.api.InstancePlugin):
    """Collect Render for Deadline"""

    order = pyblish.api.CollectorOrder + 0.01
    label = "Collect 3dmax Render Layers"
    hosts = ['max']
    families = ["maxrender"]

    def process(self, instance):
        context = instance.context
        folder = rt.maxFilePath
        file = rt.maxFileName
        current_file = os.path.join(folder, file)
        filepath = current_file.replace("\\", "/")

        context.data['currentFile'] = current_file
        asset = legacy_io.Session["AVALON_ASSET"]

        render_layer_files = RenderProducts().render_product(instance.name)
        folder = folder.replace("\\", "/")

        imgFormat = RenderProducts().image_format()
        renderer_class = get_current_renderer()
        renderer_name = str(renderer_class).split(":")[0]
        # setup the plugin as 3dsmax for the internal renderer
        if (
            renderer_name == "ART_Renderer" or
            renderer_name == "Default_Scanline_Renderer" or
            renderer_name == "Quicksilver_Hardware_Renderer"
        ):
            plugin = "3dsmax"

        if (
            renderer_name == "V_Ray_6_Hotfix_3" or
            renderer_name == "V_Ray_GPU_6_Hotfix_3"
        ):
            plugin = "Vray"

        if renderer_name == "Redshift Renderer":
            plugin = "redshift"

        if renderer_name == "Arnold":
            plugin = "arnold"

        data = {
            "subset": instance.name,
            "asset": asset,
            "publish": True,
            "imageFormat": imgFormat,
            "family": 'maxrender',
            "families": ['maxrender'],
            "source": filepath,
            "files": render_layer_files,
            "plugin": plugin,
            "frameStart": context.data['frameStart'],
            "frameEnd": context.data['frameEnd']
        }
        self.log.info("data: {0}".format(data))
        instance.data.update(data)
