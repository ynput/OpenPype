import pyblish.api
import pype.api


class ValidateTextureHasWorkfile(pyblish.api.InstancePlugin):
    """Validates that textures have appropriate workfile attached."""
    label = "Validate Texture Has Workfile"
    hosts = ["standalonepublisher"]
    order = pype.api.ValidateContentsOrder
    families = ["textures"]
    optional = True

    def process(self, instance):
        wfile = instance.data["versionData"]["workfile"]

        assert "DUMMY" not in wfile,\
            "Textures are missing attached workfile"
