import os

import pyblish.api


class CollectCelactionRender(pyblish.api.ContextPlugin):
    """ Adds the celaction render instances """

    label = "Collect Celaction Render Instance"
    order = pyblish.api.CollectorOrder + 0.1

    def process(self, context):
        project_entity = context.data["projectEntity"]
        asset_entity = context.data["assetEntity"]

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

        # add assetEntity data into instance
        instance.data.update({
            "subset": "renderAnimationMain",
            "asset": asset_entity["name"],
            "frameStart": asset_entity["data"]["frameStart"],
            "frameEnd": asset_entity["data"]["frameEnd"],
            "handleStart": asset_entity["data"]["handleStart"],
            "handleEnd": asset_entity["data"]["handleEnd"],
            "fps": asset_entity["data"]["fps"],
            "resolutionWidth": asset_entity["data"]["resolutionWidth"],
            "resolutionHeight": asset_entity["data"]["resolutionHeight"],
            "pixelAspect": 1,
            "step": 1
        })

        data = context.data.get("kwargs", {}).get("data", {})

        if data:
            instance.data.update(data)
