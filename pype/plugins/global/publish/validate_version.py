import pyblish


class ValidateVersion(pyblish.api.InstancePlugin):
    """Validate instance version.

    Pype is not allowing overwiting previously published versions.
    """

    order = pyblish.api.ValidatorOrder

    label = "Validate Version"

    def process(self, instance):
        version = int(instance.data.get("version"))
        last_version = int(instance.data.get("lastVersion"))

        assert (version != last_version), "This workfile version is already in published: database: `{0}`, workfile: `{1}`".format(last_version, version)
