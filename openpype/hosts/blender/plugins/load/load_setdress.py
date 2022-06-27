"""Load a setdress in Blender."""

from openpype.hosts.blender.plugins.load import load_layout_blend


class BlendSetdressLoader(load_layout_blend.BlendLayoutLoader):
    """Load setdress from a .blend file."""

    families = ["setdress"]
    representations = ["blend"]

    label = "Link SetDress"
    icon = "code-fork"
    color = "orange"
    color_tag = "COLOR_06"
