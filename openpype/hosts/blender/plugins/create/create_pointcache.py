"""Create a pointcache asset."""

from openpype.hosts.blender.api import plugin


class CreatePointcache(plugin.Creator):
    """Polygonal static geometry"""

    name = "pointcacheMain"
    label = "Point Cache"
    family = "pointcache"
    icon = "gears"
