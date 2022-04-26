import pyblish.api


class ValidateVersion(pyblish.api.InstancePlugin):
    """Validate instance version.

    Pype is not allowing overwiting previously published versions.
    """

    order = pyblish.api.ValidatorOrder

    label = "Validate Version"
    hosts = ["nuke", "maya", "houdini", "blender", "standalonepublisher"]

    optional = False
    active = True

    def process(self, instance):
        version = instance.data.get("version")
        latest_version = instance.data.get("latestVersion")

        if latest_version is not None:
            msg = (
                "Version `{0}` from instance `{1}` that you are trying to"
                " publish, already exists in the database. Version in"
                " database: `{2}`. Please version up your workfile to a higher"
                " version number than: `{2}`."
            ).format(version, instance.data["name"], latest_version)
            assert (int(version) > int(latest_version)), msg
