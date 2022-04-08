import os
from avalon import api
import pyblish.api
from openpype.lib import get_subset_name_with_asset_doc


class CollectWorkfile(pyblish.api.ContextPlugin):
    """ Adds the AE render instances """

    label = "Collect After Effects Workfile Instance"
    order = pyblish.api.CollectorOrder + 0.1

    def process(self, context):
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
        subset = get_subset_name_with_asset_doc(
            family,
            "",
            context.data["anatomyData"]["task"]["name"],
            context.data["assetEntity"],
            context.data["anatomyData"]["project"]["name"],
            host_name=context.data["hostName"]
        )
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

        # creating representation
        representation = {
            'name': 'aep',
            'ext': 'aep',
            'files': scene_file,
            "stagingDir": staging_dir,
        }

        instance.data["representations"].append(representation)

        self.log.info('Publishing After Effects workfile')

        for i in context:
            self.log.debug(f"{i.data['families']}")
