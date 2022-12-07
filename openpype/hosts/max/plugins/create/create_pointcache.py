# -*- coding: utf-8 -*-
"""Creator plugin for creating pointcache alembics."""
from openpype.hosts.max.api import plugin
from openpype.pipeline import CreatedInstance


class CreatePointCache(plugin.MaxCreator):
    identifier = "io.openpype.creators.max.pointcache"
    label = "Point Cache"
    family = "pointcache"
    icon = "gear"

    def create(self, subset_name, instance_data, pre_create_data):
        from pymxs import runtime as rt

        instance = super(CreatePointCache, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance

        # for additional work on the node:
        # instance_node = rt.getNodeByName(instance.get("instance_node"))
