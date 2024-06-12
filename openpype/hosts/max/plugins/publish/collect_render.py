# -*- coding: utf-8 -*-
"""Collect Render"""
import os
import pyblish.api

from pymxs import runtime as rt
from openpype.pipeline.publish import KnownPublishError
from openpype.hosts.max.api import colorspace
from openpype.hosts.max.api.lib import get_max_version, get_current_renderer
from openpype.hosts.max.api.lib_rendersettings import RenderSettings
from openpype.hosts.max.api.lib_renderproducts import RenderProducts


class CollectRender(pyblish.api.InstancePlugin):
    """Collect Render for Deadline"""

    order = pyblish.api.CollectorOrder + 0.02
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

        if instance.data.get("multiCamera"):
            cameras = instance.data.get("members")
            if not cameras:
                raise KnownPublishError("There should be at least"
                                        " one renderable camera in container")
            sel_cam = [
                c.name for c in cameras
                if rt.classOf(c) in rt.Camera.classes]
            container_name = instance.data.get("instance_node")
            render_dir = os.path.dirname(rt.rendOutputFilename)
            outputs = RenderSettings().batch_render_layer(
                container_name, render_dir, sel_cam
            )

            instance.data["cameras"] = sel_cam

            files_by_aov = RenderProducts().get_multiple_beauty(
                outputs, sel_cam)
            aovs = RenderProducts().get_multiple_aovs(
                outputs, sel_cam)
            files_by_aov.update(aovs)

        if "expectedFiles" not in instance.data:
            instance.data["expectedFiles"] = list()
            instance.data["files"] = list()
            instance.data["expectedFiles"].append(files_by_aov)
            instance.data["files"].append(files_by_aov)

        img_format = RenderProducts().image_format()
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
            "asset": instance.data["asset"],
            "subset": str(instance.name),
            "publish": True,
            "maxversion": str(get_max_version()),
            "imageFormat": img_format,
            "family": 'maxrender',
            "families": ['maxrender'],
            "renderer": renderer,
            "source": filepath,
            "plugin": "3dsmax",
            "frameStart": instance.data["frameStartHandle"],
            "frameEnd": instance.data["frameEndHandle"],
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
