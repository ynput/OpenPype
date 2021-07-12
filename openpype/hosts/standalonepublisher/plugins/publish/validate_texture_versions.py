import pyblish.api
import openpype.api


class ValidateTextureBatchVersions(pyblish.api.InstancePlugin):
    """Validates that versions match in workfile and textures."""
    label = "Validate Texture Batch Versions"
    hosts = ["standalonepublisher"]
    order = openpype.api.ValidateContentsOrder
    families = ["textures"]
    optional = True

    def process(self, instance):
        wfile = instance.data["versionData"]["workfile"]

        version_str = "v{:03d}".format(instance.data["version"])
        if 'DUMMY' in wfile:
            self.log.warning("Textures are missing attached workfile")
        else:
            msg = "Not matching version: texture v{:03d} - workfile {}"
            assert version_str in wfile, \
                msg.format(
                    instance.data["version"], wfile
                )
