# -*- coding: utf-8 -*-
"""Creator plugin for creating camera."""
from openpype.hosts.max.api import plugin
from openpype.pipeline import CreatedInstance


class CreateRedshiftProxy(plugin.MaxCreator):
    identifier = "io.openpype.creators.max.redshiftproxy"
    label = "Redshift Proxy"
    family = "redshiftproxy"
    icon = "gear"

    def create(self, subset_name, instance_data, pre_create_data):
        from pymxs import runtime as rt
        sel_obj = list(rt.selection)
        instance = super(CreateRedshiftProxy, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance
        container = rt.getNodeByName(instance.data.get("instance_node"))

        for obj in sel_obj:
            obj.parent = container
