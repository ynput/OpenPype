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

    def __init__(self, *args, **kwargs):
        super(CreateLook, self).__init__(*args, **kwargs)

        self.data["renderlayer"] = lib.get_current_renderlayer()

        # Whether to automatically convert the textures to .tx upon publish.
        self.data["maketx"] = self.make_tx

        # Enable users to force a copy.
        self.data["forceCopy"] = False
