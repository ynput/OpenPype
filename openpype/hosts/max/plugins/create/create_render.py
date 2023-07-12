# -*- coding: utf-8 -*-
"""Creator plugin for creating camera."""
import os
from openpype.hosts.max.api import plugin
from openpype.hosts.max.api.lib_rendersettings import RenderSettings


class CreateRender(plugin.MaxCreator):
    """Creator plugin for Renders."""
    identifier = "io.openpype.creators.max.render"
    label = "Render"
    family = "maxrender"
    icon = "gear"

    def create(self, subset_name, instance_data, pre_create_data):
        from pymxs import runtime as rt
        file = rt.maxFileName
        filename, _ = os.path.splitext(file)
        instance_data["AssetName"] = filename
        num_of_renderlayer =  rt.batchRenderMgr.numViews
        if num_of_renderlayer > 0:
            rt.batchRenderMgr.DeleteView(num_of_renderlayer)

        instance = super(CreateRender, self).create(
            subset_name,
            instance_data,
            pre_create_data)

        container_name = instance.data.get("instance_node")
        # set output paths for rendering(mandatory for deadline)
        RenderSettings().render_output(container_name)
