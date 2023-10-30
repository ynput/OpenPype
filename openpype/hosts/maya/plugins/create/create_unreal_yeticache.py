from openpype.hosts.maya.api import (
    lib,
    plugin
)
from openpype.lib import NumberDef


class CreateYetiCache(plugin.MayaCreator):
    """Output for procedural plugin nodes of Yeti """

    identifier = "io.openpype.creators.maya.unrealyeticache"
    label = "Unreal - Yeti Cache"
    family = "yeticacheUE"
    icon = "pagelines"

    def get_instance_attr_defs(self):

        defs = [
            NumberDef("preroll",
                      label="Preroll",
                      minimum=0,
                      default=0,
                      decimals=0)
        ]

        # Add animation data without step and handles
        defs.extend(lib.collect_animation_defs())
        remove = {"step", "handleStart", "handleEnd"}
        defs = [attr_def for attr_def in defs if attr_def.key not in remove]

        # Add samples after frame range
        defs.append(
            NumberDef("samples",
                      label="Samples",
                      default=3,
                      decimals=0)
        )

        return defs
