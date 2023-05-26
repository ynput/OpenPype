# -*- coding: utf-8 -*-
"""Collect Render"""
import os
import pyblish.api

from pymxs import runtime as rt
from openpype.pipeline import get_current_asset_name
from openpype.hosts.max.api import colorspace
from openpype.hosts.max.api.lib import get_max_version, get_current_renderer
from openpype.hosts.max.api.lib_renderproducts import RenderProducts
from openpype.client import get_last_version_by_subset_name


class CollectRender(pyblish.api.InstancePlugin):
    """Collect Render for Deadline"""

    order = pyblish.api.CollectorOrder + 0.01
    label = "Collect 3dsmax Render Layers"
    hosts = ['max']
    families = ["maxrender"]

    def process(self, instance):
        context = instance.context
        folder = rt.maxFilePath
        file = rt.maxFileName
        current_file = os.path.join(folder, file)
        filepath = current_file.replace("\\", "/")

        context.data['currentFile'] = current_file
        asset = get_current_asset_name()

        renderer_class = get_current_renderer()
        renderer = str(renderer_class).split(":")[0]
        beauty_list, aov_list = RenderProducts().render_product(instance.name)
        full_render_list = list()
        if aov_list:
            full_render_list.extend(iter(beauty_list))
            full_render_list.extend(iter(aov_list))

        else:
            full_render_list = beauty_list

        files_by_aov = {
            "_": beauty_list
        }

        folder = folder.replace("\\", "/")
        if aov_list:
            if renderer in [
                "ART_Renderer",
                "V_Ray_6_Hotfix_3",
                "V_Ray_GPU_6_Hotfix_3"
                "Redshift_Renderer",
                "Default_Scanline_Renderer",
                "Quicksilver_Hardware_Renderer",
            ]:

                render_element = RenderProducts().get_aov()
                files_by_aov.update(render_element)
                self.log.debug(files_by_aov)

            if renderer == "Arnold":
                aovs = RenderProducts().get_aovs()
                files_by_aov.update(aovs)

        if "expectedFiles" not in instance.data:
            instance.data["expectedFiles"] = list()
            instance.data["expectedFiles"].append(files_by_aov)

        img_format = RenderProducts().image_format()
        project_name = context.data["projectName"]
        asset_doc = context.data["assetEntity"]
        asset_id = asset_doc["_id"]
        version_doc = get_last_version_by_subset_name(project_name,
                                                      instance.name,
                                                      asset_id)
        self.log.debug("version_doc: {0}".format(version_doc))
        version_int = 1
        if version_doc:
            version_int += int(version_doc["name"])

        self.log.debug(f"Setting {version_int} to context.")
        context.data["version"] = version_int
        # OCIO config not support in
        # most of the 3dsmax renderers
        # so this is currently hard coded
        setting = instance.context.data["project_settings"]
        image_io = setting["global"]["imageio"]
        instance.data["colorspaceConfig"] = image_io["ocio_config"]["filepath"][0]     # noqa
        instance.data["colorspaceDisplay"] = "sRGB"
        instance.data["colorspaceView"] = "ACES 1.0"
        instance.data["renderProducts"] = colorspace.ARenderProduct()
        instance.data["attachTo"] = []

        data = {
            "subset": instance.name,
            "asset": asset,
            "publish": True,
            "maxversion": str(get_max_version()),
            "imageFormat": img_format,
            "family": 'maxrender',
            "families": ['maxrender'],
            "source": filepath,
            "files": full_render_list,
            "plugin": "3dsmax",
            "frameStart": int(rt.rendStart),
            "frameEnd": int(rt.rendEnd),
            "version": version_int,
            "farm": True
        }
        instance.data.update(data)
        self.log.info("data: {0}".format(data))
        files = instance.data["expectedFiles"]
        self.log.debug("expectedFiles: {0}".format(files))
