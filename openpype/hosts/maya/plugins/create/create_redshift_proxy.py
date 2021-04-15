# -*- coding: utf-8 -*-
"""Creator of Redshift proxy subset types."""

from openpype.hosts.maya.api import plugin, lib


class CreateRedshiftProxy(plugin.Creator):
    """Create instance of Redshift Proxy subset."""

    name = "redshiftproxy"
    label = "Redshift Proxy"
    family = "redshiftproxy"
    icon = "gears"

    def __init__(self, *args, **kwargs):
        super(CreateRedshiftProxy, self).__init__(*args, **kwargs)

        animation_data = lib.collect_animation_data()

        self.data["animation"] = False
        self.data["proxyFrameStart"] = animation_data["frameStart"]
        self.data["proxyFrameEnd"] = animation_data["frameEnd"]
        self.data["proxyFrameStep"] = animation_data["step"]
