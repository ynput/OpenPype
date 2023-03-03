# -*- coding: utf-8 -*-
"""Creator plugin for model exported in USD format."""
from openpype.hosts.max.api import plugin
from openpype.pipeline import CreatedInstance


class CreateUSDModel(plugin.MaxCreator):
    identifier = "io.openpype.creators.max.usdmodel"
    label = "USD Model"
    family = "usdmodel"
    icon = "gear"

    def create(self, subset_name, instance_data, pre_create_data):
        from pymxs import runtime as rt
        _ = super(CreateUSDModel, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance
        # TODO: Disable "Add to Containers?" Panel
        # parent the selected cameras into the container
        # for additional work on the node:
        # instance_node = rt.getNodeByName(instance.get("instance_node"))
