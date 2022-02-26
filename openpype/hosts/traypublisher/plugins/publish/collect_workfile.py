import os
import pyblish.api


class CollectWorkfile(pyblish.api.InstancePlugin):
    """Collect representation of workfile instances."""

    label = "Collect Workfile"
    order = pyblish.api.CollectorOrder - 0.49
    families = ["workfile"]
    hosts = ["traypublisher"]

    def process(self, instance):
        if "representations" not in instance.data:
            instance.data["representations"] = []
        repres = instance.data["representations"]

        creator_attributes = instance.data["creator_attributes"]
        filepath = creator_attributes["filepath"]
        instance.data["sourceFilepath"] = filepath

        staging_dir = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
        ext = os.path.splitext(filename)[-1]

        repres.append({
            "ext": ext,
            "name": ext,
            "stagingDir": staging_dir,
            "files": filename
        })
