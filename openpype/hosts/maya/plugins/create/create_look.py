from openpype.hosts.maya.api import (
    plugin,
    lib
)
from openpype.lib import (
    BoolDef,
    TextDef
)


class CreateLook(plugin.MayaCreator):
    """Shader connections defining shape look"""

    identifier = "io.openpype.creators.maya.look"
    label = "Look"
    family = "look"
    icon = "paint-brush"

    make_tx = True
    rs_tex = False

    def get_instance_attr_defs(self):

        return [
            # TODO: This value should actually get set on create!
            TextDef("renderLayer",
                    # TODO: Bug: Hidden attribute's label is still shown in UI?
                    hidden=True,
                    default=lib.get_current_renderlayer(),
                    label="Renderlayer",
                    tooltip="Renderlayer to extract the look from"),
            BoolDef("maketx",
                    label="MakeTX",
                    tooltip="Whether to generate .tx files for your textures",
                    default=self.make_tx),
            BoolDef("rstex",
                    label="Convert textures to .rstex",
                    tooltip="Whether to generate Redshift .rstex files for "
                            "your textures",
                    default=self.rs_tex)
        ]

    def get_pre_create_attr_defs(self):
        # Show same attributes on create but include use selection
        defs = super(CreateLook, self).get_pre_create_attr_defs()
        defs.extend(self.get_instance_attr_defs())
        return defs
