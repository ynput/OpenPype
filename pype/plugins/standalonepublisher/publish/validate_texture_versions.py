import pyblish.api
import pype.api


class ValidateTextureBatchVersions(pyblish.api.InstancePlugin):
    """Validates that versions match in workfile and textures.

        Workfile is optional, so if you are sure, you can disable this
        validator after Refresh.

        Validates that only single version is published at a time.
    """
    label = "Validate Texture Batch Versions"
    hosts = ["standalonepublisher"]
    order = pype.api.ValidateContentsOrder
    families = ["textures"]
    optional = True

    def process(self, instance):
        wfile = instance.data["versionData"]["workfile"]

        version_str = "v{:03d}".format(instance.data["version"])

        msg = "Not matching version: texture v{:03d} - workfile {}"
        assert version_str in wfile, \
            msg.format(
                instance.data["version"], wfile
            )

        present_versions = []
        for instance in instance.context:
            present_versions.append(instance.data["version"])

        assert len(present_versions) == 1, "Too many versions in a batch!"
