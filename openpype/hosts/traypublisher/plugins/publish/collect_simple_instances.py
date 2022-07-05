import os
import pyblish.api


class CollectSettingsSimpleInstances(pyblish.api.InstancePlugin):
    """Collect data for instances created by settings creators."""

    label = "Collect Settings Simple Instances"
    order = pyblish.api.CollectorOrder - 0.49

    hosts = ["traypublisher"]

    def process(self, instance):
        if not instance.data.get("settings_creator"):
            return

        if "families" not in instance.data:
            instance.data["families"] = []

        if "representations" not in instance.data:
            instance.data["representations"] = []
        repres = instance.data["representations"]

        creator_attributes = instance.data["creator_attributes"]
        filepath_item = creator_attributes["filepath"]
        self.log.info(filepath_item)
        filepaths = [
            os.path.join(filepath_item["directory"], filename)
            for filename in filepath_item["filenames"]
        ]

        instance.data["sourceFilepaths"] = filepaths
        instance.data["stagingDir"] = filepath_item["directory"]

        filenames = filepath_item["filenames"]
        _, ext = os.path.splitext(filenames[0])
        ext = ext[1:]
        if len(filenames) == 1:
            filenames = filenames[0]

        repres.append({
            "ext": ext,
            "name": ext,
            "stagingDir": filepath_item["directory"],
            "files": filenames
        })

        self.log.debug("Created Simple Settings instance {}".format(
            instance.data
        ))
