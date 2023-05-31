# -*- coding: utf-8 -*-
"""Collect Render"""
import os
import pyblish.api

from pymxs import runtime as rt
from openpype.pipeline import get_current_asset_name
from openpype.hosts.max.api.lib import get_max_version
from openpype.hosts.max.api.lib_renderproducts import RenderProducts
from openpype.client import get_last_version_by_subset_name
from openpype.lib import (
    TextDef,
    BoolDef,
    NumberDef,
)
from openpype.pipeline import OpenPypePyblishPluginMixin


class CollectRender(pyblish.api.InstancePlugin, OpenPypePyblishPluginMixin):
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

        render_layer_files = RenderProducts().render_product(instance.name)

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
        # setup the plugin as 3dsmax for the internal renderer
        data = {
            "subset": instance.name,
            "asset": asset,
            "publish": True,
            "maxversion": str(get_max_version()),
            "imageFormat": img_format,
            "family": 'maxrender',
            "families": ['maxrender'],
            "source": filepath,
            "expectedFiles": render_layer_files,
            "plugin": "3dsmax",
            "frameStart": int(rt.rendStart),
            "frameEnd": int(rt.rendEnd),
            "version": version_int,
            "farm": True
        }

        attr_data = self.get_attr_values_from_data(instance.data)
        if attr_data.get("use_custom_range", False):
            self._change_custom_range(attr_data, data)
        instance.data.update(data)

        # TODO: this should be unified with maya and its "multipart" flag
        #       on instance.
        if renderer == "Redshift_Renderer":
            instance.data.update(
                {"separateAovFiles": rt.Execute(
                    "renderers.current.separateAovFiles")})

        self.log.info("data: {0}".format(data))

    # TODO Rename this here and in `process`

    @staticmethod
    def _change_custom_range(attr_data, data):
        data["frameStart"] = attr_data.get("customStart", 0)
        data["frameEnd"] = attr_data.get("customEnd", 0)
        data["handleStart"] = attr_data.get("customHandlesStart", 0)
        data["handleEnd"] = attr_data.get("customHandlesEnd", 0)
        data["frameStartHandle"] = data["frameStart"] - data["handleStart"]
        data["frameEndHandle"] = data["frameEnd"] + data["handleEnd"]

    @classmethod
    def get_attribute_defs(cls):
        defs = super(CollectRender, cls).get_attribute_defs()
        defs.extend([
            BoolDef("use_custom_range",
                    label="Use Custom Frame Range"),
            NumberDef("customStart",
                      decimals=0,
                      label="Frame Start"),
            NumberDef("customEnd",
                      decimals=0,
                      label="Frame End"),
            NumberDef("customHandlesStart",
                      decimals=0,
                      label="Handles Start"),
            NumberDef("customHandlesEnd",
                      decimals=0,
                      label="Handles End"),
        ])

        return defs
