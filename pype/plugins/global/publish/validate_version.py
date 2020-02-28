import pyblish


class ValidateVersion(pyblish.api.InstancePlugin):
    """Validate instance version.

    Pype is not allowing overwiting previously published versions.
    """

    order = pyblish.api.ValidatorOrder

    label = "Validate Version"
    hosts = ["nuke", "maya", "blender"]

    def process(self, instance):
        version = int(instance.data.get("version")
        latest_version = int(instance.data.get("latestVersion", 0))

        assert (version != latest_version), ("Version `{0}` that you are"
                                           " trying to publish, already"
                                           " exists in the"
                                           " database `{1}`.").format(
                                            version, latest_version)
