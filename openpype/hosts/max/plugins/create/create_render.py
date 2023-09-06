# -*- coding: utf-8 -*-
"""Creator plugin for creating camera."""
from openpype.hosts.max.api import plugin
from openpype.pipeline import CreatedInstance
from openpype.hosts.max.api.lib_rendersettings import RenderSettings


class CreateRender(plugin.MaxCreator):
    identifier = "io.openpype.creators.max.render"
    label = "Render"
    family = "maxrender"
    icon = "gear"

    def create(self, subset_name, instance_data, pre_create_data):
        from pymxs import runtime as rt
        sel_obj = list(rt.selection)
        instance = super(CreateRender, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance
        container_name = instance.data.get("instance_node")
        container = rt.getNodeByName(container_name)
        # TODO: Disable "Add to Containers?" Panel
        # parent the selected cameras into the container
        for obj in sel_obj:
            obj.parent = container
        # for additional work on the node:
        # instance_node = rt.getNodeByName(instance.get("instance_node"))

        # make sure the render dialog is closed
        # for the update of resolution
        # Changing the Render Setup dialog settings should be done
        # with the actual Render Setup dialog in a closed state.

        # set viewport camera for rendering(mandatory for deadline)
        RenderSettings().set_render_camera(sel_obj)
        # set output paths for rendering(mandatory for deadline)
        RenderSettings().render_output(container_name)
