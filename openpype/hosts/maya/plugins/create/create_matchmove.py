from openpype.hosts.maya.api import (
    lib,
    plugin
)
from openpype.lib import BoolDef


class CreateMatchmove(plugin.MayaCreator):
    """Instance for more complex setup of cameras.

    Might contain multiple cameras, geometries etc.

    It is expected to be extracted into .abc or .ma
    """

    identifier = "io.openpype.creators.maya.matchmove"
    label = "Matchmove"
    family = "matchmove"
    icon = "video-camera"

    def get_instance_attr_defs(self):

        defs = lib.collect_animation_defs()

        defs.extend([
            BoolDef("bakeToWorldSpace",
                    label="Bake Cameras to World-Space",
                    tooltip="Bake Cameras to World-Space",
                    default=True),
        ])

        return defs
