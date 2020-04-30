import os

import pyblish.api


class CollectCelactionRender(pyblish.api.ContextPlugin):
    """ Adds the celaction render instances """

    order = pyblish.api.CollectorOrder + 0.1

    def process(self, context):

        # scene render
        scene_file = os.path.basename(context.data["currentFile"])
        scene_name, _ = os.path.splitext(scene_file)
        component_name = scene_name.split(".")[0]

        instance = context.create_instance(name=component_name)
        instance.data["family"] = "render"
        instance.data["label"] = "{} - remote".format(component_name)
        instance.data["families"] = ["render", "img"]

        # getting instance state
        instance.data["publish"] = True

        data = context.data("kwargs")["data"]

        for item in data:
            instance.set_data(item, value=data[item])
