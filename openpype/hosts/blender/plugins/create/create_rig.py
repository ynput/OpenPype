"""Create a rig asset."""

from openpype.hosts.blender.api import plugin


class CreateRig(plugin.Creator):
    """Artist-friendly rig with controls to direct motion"""

    name = "rigMain"
    label = "Rig"
    family = "rig"
    icon = "wheelchair"
    defaults = ["Main", "Proxy"]
    color_tag = "COLOR_03"
