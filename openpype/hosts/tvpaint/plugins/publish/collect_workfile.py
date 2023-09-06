import os
import json
import pyblish.api


class CollectWorkfile(pyblish.api.InstancePlugin):
    label = "Collect Workfile"
    order = pyblish.api.CollectorOrder - 0.4
    hosts = ["tvpaint"]
    families = ["workfile"]

    def process(self, instance):
        context = instance.context
        current_file = context.data["currentFile"]

        self.log.info(
            "Workfile path used for workfile family: {}".format(current_file)
        )

        dirpath, filename = os.path.split(current_file)
        basename, ext = os.path.splitext(filename)

        instance.data["representations"].append({
            "name": ext.lstrip("."),
            "ext": ext.lstrip("."),
            "files": filename,
            "stagingDir": dirpath
        })

        self.log.info("Collected workfile instance: {}".format(
            json.dumps(instance.data, indent=4)
        ))
