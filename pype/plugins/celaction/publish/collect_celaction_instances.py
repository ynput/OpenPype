import os
from avalon import api
import pyblish.api


class CollectCelactionInstances(pyblish.api.ContextPlugin):
    """ Adds the celaction render instances """

    label = "Collect Celaction Instances"
    order = pyblish.api.CollectorOrder + 0.1

    def process(self, context):
        task = api.Session["AVALON_TASK"]
        current_file = context.data["currentFile"]
        staging_dir = os.path.dirname(current_file)
        scene_file = os.path.basename(current_file)

        asset_entity = context.data["assetEntity"]

        shared_instance_data = {
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
        }

        celaction_kwargs = context.data.get("kwargs", {})

        if celaction_kwargs:
            shared_instance_data.update(celaction_kwargs)

        # ___________________________________________
        # workfile instance
        family = "workfile"
        subset = family + task.capitalize()
        # Create instance
        instance = context.create_instance(subset)

        # creating instance data
        instance.data.update({
            "subset": subset,
            "label": scene_file,
            "family": family,
            "families": [],
            "representations": list()
        })

        # adding basic script data
        instance.data.update(shared_instance_data)

        # creating representation
        representation = {
            'name': 'scn',
            'ext': 'scn',
            'files': scene_file,
            "stagingDir": staging_dir,
        }

        instance.data["representations"].append(representation)

        self.log.info('Publishing Celaction workfile')
        context.data["instances"].append(instance)

        # ___________________________________________
        # render instance
        subset = f"render{task}Main"
        instance = context.create_instance(name=subset)
        # getting instance state
        instance.data["publish"] = True

        # add assetEntity data into instance
        instance.data.update({
            "label": "{} - farm".format(subset),
            "family": "render.farm",
            "families": [],
            "subset": subset
        })

        self.log.debug(f"Instance data: `{instance.data}`")
