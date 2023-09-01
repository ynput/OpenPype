# -*- coding: utf-8 -*-
"""Creator plugin for creating camera."""
import os
from openpype.hosts.max.api import plugin
from openpype.hosts.max.api.lib_rendersettings import RenderSettings
from openpype.hosts.max.api.lib import get_max_version
from openpype.lib import EnumDef
from pymxs import runtime as rt


class CreateRender(plugin.MaxCreator):
    """Creator plugin for Renders."""
    identifier = "io.openpype.creators.max.render"
    label = "Render"
    family = "maxrender"
    icon = "gear"

    def create(self, subset_name, instance_data, pre_create_data):
        sel_obj = list(rt.selection)
        file = rt.maxFileName
        filename, _ = os.path.splitext(file)
        instance = super(CreateRender, self).create(
            subset_name,
            instance_data,
            pre_create_data)
        container_name = instance.data.get("instance_node")
        sel_obj = self.selected_nodes
        if sel_obj:
            # set viewport camera for rendering(mandatory for deadline)
            RenderSettings(self.project_settings).set_render_camera(sel_obj)
        # set output paths for rendering(mandatory for deadline)
        RenderSettings().render_output(container_name)

    def get_instance_attr_defs(self):
        ocio_display_view_transform_list = ["sRGB||ACES 1.0 SDR-video"]
        if int(get_max_version()) >= 2024:
            display_view_default = ""
            ocio_display_view_transform_list = []
            colorspace_mgr = rt.ColorPipelineMgr
            displays = colorspace_mgr.GetDisplayList()
            for display in sorted(displays):
                views = colorspace_mgr.GetViewList(display)
                for view in sorted(views):
                    ocio_display_view_transform_list.append({
                        "value": "||".join((display, view))
                    })
                    if display == "ACES" and view == "sRGB":
                        display_view_default = "{0}||{1}".format(
                            display, view
                        )

        return [
            EnumDef("ocio_display_view_transform",
                    ocio_display_view_transform_list,
                    default=display_view_default,
                    label="OCIO Displays and Views")
        ]
