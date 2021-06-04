import os
import json
import pyblish.api
from avalon import io


class CollectWorkfile(pyblish.api.ContextPlugin):
    label = "Collect Workfile"
    order = pyblish.api.CollectorOrder - 1
    hosts = ["tvpaint"]

    def process(self, context):
        current_file = context.data["currentFile"]

        self.log.info(
            "Workfile path used for workfile family: {}".format(current_file)
        )

        dirpath, filename = os.path.split(current_file)
        basename, ext = os.path.splitext(filename)
        instance = context.create_instance(name=basename)

        task_name = io.Session["AVALON_TASK"]
        subset_name = "workfile" + task_name.capitalize()

        # Create Workfile instance
        instance.data.update({
            "subset": subset_name,
            "asset": context.data["asset"],
            "label": subset_name,
            "publish": True,
            "family": "workfile",
            "families": ["workfile"],
            "representations": [{
                "name": ext.lstrip("."),
                "ext": ext.lstrip("."),
                "files": filename,
                "stagingDir": dirpath
            }]
        })
        self.log.info("Collected workfile instance: {}".format(
            json.dumps(instance.data, indent=4)
        ))
