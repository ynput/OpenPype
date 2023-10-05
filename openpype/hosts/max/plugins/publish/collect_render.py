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

        files_by_aov = RenderProducts().get_beauty(instance.name)
        aovs = RenderProducts().get_aovs(instance.name)
        files_by_aov.update(aovs)

        camera = rt.viewport.GetCamera()
        if instance.data.get("members"):
            camera_list = [member for member in instance.data["members"]
                           if rt.ClassOf(member) == rt.Camera.Classes]
            if camera_list:
                camera = camera_list[-1]

        instance.data["cameras"] = [camera.name] if camera else None        # noqa

        if "expectedFiles" not in instance.data:
            instance.data["expectedFiles"] = list()
            instance.data["files"] = list()
            instance.data["expectedFiles"].append(files_by_aov)
            instance.data["files"].append(files_by_aov)

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
        # TODO: add options for redshift/vray ocio config
        instance.data["colorspaceConfig"] = ""
        instance.data["colorspaceDisplay"] = "sRGB"
        instance.data["colorspaceView"] = "ACES 1.0 SDR-video"

        if int(get_max_version()) >= 2024:
            colorspace_mgr = rt.ColorPipelineMgr      # noqa
            display = next(
                (display for display in colorspace_mgr.GetDisplayList()))
            view_transform = next(
                (view for view in colorspace_mgr.GetViewList(display)))
            instance.data["colorspaceConfig"] = colorspace_mgr.OCIOConfigPath
            instance.data["colorspaceDisplay"] = display
            instance.data["colorspaceView"] = view_transform

        instance.data["renderProducts"] = colorspace.ARenderProduct()
        instance.data["publishJobState"] = "Suspended"
        instance.data["attachTo"] = []
        renderer_class = get_current_renderer()
        renderer = str(renderer_class).split(":")[0]
        # also need to get the render dir for conversion
        data = {
            "asset": asset,
            "subset": str(instance.name),
            "publish": True,
            "maxversion": str(get_max_version()),
            "imageFormat": img_format,
            "family": 'maxrender',
            "families": ['maxrender'],
            "renderer": renderer,
            "source": filepath,
            "plugin": "3dsmax",
            "frameStart": int(rt.rendStart),
            "frameEnd": int(rt.rendEnd),
            "version": version_int,
            "farm": True
        }
        instance.data.update(data)

        # TODO: this should be unified with maya and its "multipart" flag
        #       on instance.
        if renderer == "Redshift_Renderer":
            instance.data.update(
                {"separateAovFiles": rt.Execute(
                    "renderers.current.separateAovFiles")})

        self.log.info("data: {0}".format(data))
