import os
import re
import pyblish.api

from openpype.hosts.aftereffects.api import (
    get_stub,
    get_extension_manifest_path
)


class CollectExtensionVersion(pyblish.api.ContextPlugin):
    """ Pulls and compares version of installed extension.

        It is recommended to use same extension as in provided Openpype code.

        Please use Anastasiy’s Extension Manager or ZXPInstaller to update
        extension in case of an error.

        You can locate extension.zxp in your installed Openpype code in
        `repos/avalon-core/avalon/aftereffects`
    """
    # This technically should be a validator, but other collectors might be
    # impacted with usage of obsolete extension, so collector that runs first
    # was chosen
    order = pyblish.api.CollectorOrder - 0.5
    label = "Collect extension version"
    hosts = ["aftereffects"]

    optional = True
    active = True

    def process(self, context):
        installed_version = get_stub().get_extension_version()

        if not installed_version:
            raise ValueError("Unknown version, probably old extension")

        manifest_url = get_extension_manifest_path()

        if not os.path.exists(manifest_url):
            self.log.debug("Unable to locate extension manifest, not checking")
            return

        expected_version = None
        with open(manifest_url) as fp:
            content = fp.read()
            found = re.findall(r'(ExtensionBundleVersion=")([0-9\.]+)(")',
                               content)
            if found:
                expected_version = found[0][1]

        if expected_version != installed_version:
            msg = (
                "Expected version '{}' found '{}'\n Please update"
                " your installed extension, it might not work properly."
            ).format(expected_version, installed_version)

            raise ValueError(msg)
