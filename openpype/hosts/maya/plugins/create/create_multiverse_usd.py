from openpype.hosts.maya.api import plugin


class CreateMultiverseUsd(plugin.Creator):
    """Multiverse USD data"""

    name = "usd"
    label = "Multiverse USD"
    family = "usd"
    icon = "cubes"
