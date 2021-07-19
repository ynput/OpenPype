import pyblish.api
import openpype.api


class ValidateTextureBatchVersions(pyblish.api.InstancePlugin):
    """Validates that versions match in workfile and textures.

        Workfile is optional, so if you are sure, you can disable this
        validator after Refresh.

        Validates that only single version is published at a time.
    """
    label = "Validate Texture Batch Versions"
    hosts = ["standalonepublisher"]
    order = openpype.api.ValidateContentsOrder
    families = ["textures"]
    optional = False

    def process(self, instance):
        wfile = instance.data["versionData"].get("workfile")

        version_str = "v{:03d}".format(instance.data["version"])

        if not wfile:  # no matching workfile, do not check versions
            self.log.info("No workfile present for textures")
            return

        msg = "Not matching version: texture v{:03d} - workfile {}"
        assert version_str in wfile, \
            msg.format(
                instance.data["version"], wfile
            )

        present_versions = set()
        for instance in instance.context:
            present_versions.add(instance.data["version"])

        assert len(present_versions) == 1, "Too many versions in a batch!"
