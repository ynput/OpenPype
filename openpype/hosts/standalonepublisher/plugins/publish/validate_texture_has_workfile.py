import pyblish.api
import openpype.api


class ValidateTextureHasWorkfile(pyblish.api.InstancePlugin):
    """Validates that textures have appropriate workfile attached.

        Workfile is optional, disable this Validator after Refresh if you are
        sure it is not needed.
    """
    label = "Validate Texture Has Workfile"
    hosts = ["standalonepublisher"]
    order = openpype.api.ValidateContentsOrder
    families = ["textures"]
    optional = True

    def process(self, instance):
        wfile = instance.data["versionData"].get("workfile")

        assert wfile, "Textures are missing attached workfile"
