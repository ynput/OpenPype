from pype.hosts.maya.api import (
    lib,
    plugin
)


class CreateLook(plugin.Creator):
    """Shader connections defining shape look"""

    name = "look"
    label = "Look"
    family = "look"
    icon = "paint-brush"
    defaults = ['Main']

    def __init__(self, *args, **kwargs):
        super(CreateLook, self).__init__(*args, **kwargs)

        self.data["renderlayer"] = lib.get_current_renderlayer()

        # Whether to automatically convert the textures to .tx upon publish.
        self.data["maketx"] = True

        # Enable users to force a copy.
        self.data["forceCopy"] = False
