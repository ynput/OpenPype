# -*- coding: utf-8 -*-
"""Creator plugin for creating point cloud."""
from openpype.hosts.max.api import plugin
from openpype.pipeline import CreatedInstance


class CreatePointCloud(plugin.MaxCreator):
    identifier = "io.openpype.creators.max.pointcloud"
    label = "Point Cloud"
    family = "pointcloud"
    icon = "gear"

    def create(self, subset_name, instance_data, pre_create_data):
        from pymxs import runtime as rt
        sel_obj = list(rt.selection)
        instance = super(CreatePointCloud, self).create(
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
