import os
from avalon import api
import pyblish.api


class CollectWorkfile(pyblish.api.ContextPlugin):
    """ Adds the AE render instances """

    label = "Collect After Effects Workfile Instance"
    order = pyblish.api.CollectorOrder + 0.1

    def process(self, context):
        existing_instance = None
        for instance in context:
            if instance.data["family"] == "workfile":
                self.log.debug("Workfile instance found, won't create new")
                existing_instance = instance
                break

        task = api.Session["AVALON_TASK"]
        current_file = context.data["currentFile"]
        staging_dir = os.path.dirname(current_file)
        scene_file = os.path.basename(current_file)
        version = context.data["version"]
        asset_entity = context.data["assetEntity"]
        project_entity = context.data["projectEntity"]

        shared_instance_data = {
            "asset": asset_entity["name"],
            "frameStart": asset_entity["data"]["frameStart"],
            "frameEnd": asset_entity["data"]["frameEnd"],
            "handleStart": asset_entity["data"]["handleStart"],
            "handleEnd": asset_entity["data"]["handleEnd"],
            "fps": asset_entity["data"]["fps"],
            "resolutionWidth": asset_entity["data"].get(
                "resolutionWidth",
                project_entity["data"]["resolutionWidth"]),
            "resolutionHeight": asset_entity["data"].get(
                "resolutionHeight",
                project_entity["data"]["resolutionHeight"]),
            "pixelAspect": 1,
            "step": 1,
            "version": version
        }

        # workfile instance
        family = "workfile"
        subset = family + task.capitalize()
        if existing_instance is None:  # old publish
            # Create instance
            instance = context.create_instance(subset)

            # creating instance data
            instance.data.update({
                "subset": subset,
                "label": scene_file,
                "family": family,
                "families": [family],
                "representations": list()
            })

            # adding basic script data
            instance.data.update(shared_instance_data)
        else:
            instance = existing_instance
            instance.data["publish"] = True  # for DL

        # creating representation
        representation = {
            'name': 'aep',
            'ext': 'aep',
            'files': scene_file,
            "stagingDir": staging_dir,
        }

        instance.data["representations"].append(representation)
