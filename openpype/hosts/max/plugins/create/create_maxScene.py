# -*- coding: utf-8 -*-
"""Creator plugin for creating raw max scene."""
from openpype.hosts.max.api import plugin
from openpype.pipeline import CreatedInstance


class CreateMaxScene(plugin.MaxCreator):
    identifier = "io.openpype.creators.max.maxScene"
    label = "Max Scene"
    family = "maxScene"
    icon = "gear"

    def create(self, subset_name, instance_data, pre_create_data):
        from pymxs import runtime as rt
        sel_obj = list(rt.selection)
        instance = super(CreateMaxScene, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance
        container = rt.getNodeByName(instance.data.get("instance_node"))
        # TODO: Disable "Add to Containers?" Panel
        # parent the selected cameras into the container
        for obj in sel_obj:
            obj.parent = container
        # for additional work on the node:
        # instance_node = rt.getNodeByName(instance.get("instance_node"))
