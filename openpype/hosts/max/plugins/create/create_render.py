# -*- coding: utf-8 -*-
"""Creator plugin for creating camera."""
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
        from pymxs import runtime as rt
        file = rt.maxFileName
        filename, _ = os.path.splitext(file)
        instance_data["AssetName"] = filename

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
        if int(get_max_version()) >= 2024:
            default_value = ""
            display_views = []
            colorspace_mgr = rt.ColorPipelineMgr
            for display in sorted(colorspace_mgr.GetDisplayList()):
                for view in sorted(colorspace_mgr.GetViewList(display)):
                    display_views.append({
                        "value": "||".join((display, view))
                    })
                    if display == "ACES" and view == "sRGB":
                        default_value = "{0}||{1}".format(
                            display, view
                        )
        else:
            display_views = ["sRGB||ACES 1.0 SDR-video"]

        return [
            EnumDef("ocio_display_view_transform",
                    display_views,
                    default=default_value,
                    label="OCIO Displays and Views")
        ]
