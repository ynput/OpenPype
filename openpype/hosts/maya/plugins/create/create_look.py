from openpype.hosts.maya.api import (
    lib,
    plugin
)


class CreateLook(plugin.Creator):
    """Shader connections defining shape look"""

    name = "look"
    label = "Look"
    family = "look"
    icon = "paint-brush"
    make_tx = True
    rs_tex = False

    def __init__(self, *args, **kwargs):
        super(CreateLook, self).__init__(*args, **kwargs)

        self.data["renderlayer"] = lib.get_current_renderlayer()

        # Whether to automatically convert the textures to .tx upon publish.
        self.data["maketx"] = self.make_tx
        # Whether to automatically convert the textures to .rstex upon publish.
        self.data["rstex"] = self.rs_tex
        # Enable users to force a copy.
        # - on Windows is "forceCopy" always changed to `True` because of
        #   windows implementation of hardlinks
        self.data["forceCopy"] = False
