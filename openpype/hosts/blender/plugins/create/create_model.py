"""Create a model asset."""

from openpype.hosts.blender.api import plugin


class CreateModel(plugin.Creator):
    """Polygonal static geometry"""

    name = "modelMain"
    label = "Model"
    family = "model"
    icon = "cube"
    defaults = ["Main", "Proxy"]
