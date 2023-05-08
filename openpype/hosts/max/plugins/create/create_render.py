# -*- coding: utf-8 -*-
"""Creator plugin for creating camera."""
from openpype.hosts.max.api import plugin
from openpype.hosts.max.api.lib_rendersettings import RenderSettings


class CreateRender(plugin.MaxCreator):
    """Creator plugin for Renders."""
    identifier = "io.openpype.creators.max.render"
    label = "Render"
    family = "maxrender"
    icon = "gear"

    def create(self, subset_name, instance_data, pre_create_data):
        """Plugin entry point."""
        from pymxs import runtime as rt  # noqa: WPS433,I001
        instance = super().create(
            subset_name,
            instance_data,
            pre_create_data)
        container_name = instance.data.get("instance_node")
        # TODO: Disable "Add to Containers?" Panel
        # parent the selected cameras into the container
        sel_obj = self.selected_nodes
        if sel_obj:
            # set viewport camera for rendering(mandatory for deadline)
            RenderSettings().set_render_camera(sel_obj)
        # set output paths for rendering(mandatory for deadline)
        RenderSettings().render_output(container_name)
