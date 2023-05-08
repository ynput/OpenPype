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

        _ = super(CreateRedshiftProxy, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance
