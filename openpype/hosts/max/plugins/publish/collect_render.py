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
        # setup the plugin as 3dsmax for the internal renderer
        data = {
            "subset": instance.name,
            "asset": asset,
            "publish": True,
            "imageFormat": imgFormat,
            "family": 'maxrender',
            "families": ['maxrender'],
            "source": filepath,
            "files": render_layer_files,
            "plugin": "3dsmax",
            "frameStart": context.data['frameStart'],
            "frameEnd": context.data['frameEnd']
        }
        self.log.info("data: {0}".format(data))
        instance.data.update(data)
