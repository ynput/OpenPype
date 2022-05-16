"""Load a Set Dress in Blender."""

from openpype.hosts.blender.plugins.load.load_layout_blend import (
    BlendLayoutLoader
)


class BlendSetdressLoader(BlendLayoutLoader):
    """Load Set Dress from a .blend file."""

    families = ["setdress"]
    representations = ["blend"]

    label = "Link SetDress"
    icon = "code-fork"
    color = "orange"
    color_tag = "COLOR_06"
