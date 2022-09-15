import pyblish.api


class CollectVersion(pyblish.api.InstancePlugin):
    """Collect version for publishable instances.

    Used to synchronize version from workfile to all publishable instances:
        - image (manually created or color coded)
        - review

    Dev comment:
    Explicit collector created to control this from single place and not from
    3 different.
    """
    order = pyblish.api.CollectorOrder + 0.200
    label = 'Collect Version'

    hosts = ["photoshop"]
    families = ["image", "review"]

    # controlled by Settings
    sync_workfile_version = False

    def process(self, instance):
        if self.sync_workfile_version:
            workfile_version = instance.context.data["version"]
            self.log.debug(f"Applying version {workfile_version}")
            instance.data["version"] = workfile_version
