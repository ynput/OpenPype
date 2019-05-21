import os
import pyblish.api
from avalon import (
    io,
    api as avalon
)
import json
import logging
import clique


log = logging.getLogger("collector")


class CollectContextDataSAPublish(pyblish.api.ContextPlugin):
    """
    Collecting temp json data sent from a host context
    and path for returning json data back to hostself.

    Setting avalon session into correct context

    Args:
        context (obj): pyblish context session

    """

    label = "Collect Context - SA Publish"
    order = pyblish.api.CollectorOrder - 0.49

    def process(self, context):
        # get json paths from os and load them
        io.install()
        input_json_path = os.environ.get("SAPUBLISH_INPATH")
        output_json_path = os.environ.get("SAPUBLISH_OUTPATH")

        context.data["stagingDir"] = os.path.dirname(input_json_path)
        context.data["returnJsonPath"] = output_json_path

        with open(input_json_path, "r") as f:
            in_data = json.load(f)

        project_name = in_data['project']
        asset_name = in_data['asset']
        family = in_data['family']
        subset = in_data['subset']

        project = io.find_one({'type': 'project'})
        asset = io.find_one({
            'type': 'asset',
            'name': asset_name
        })
        context.data['project'] = project
        context.data['asset'] = asset

        instance = context.create_instance(subset)

        instance.data.update({
            "subset": subset,
            "asset": asset_name,
            "label": subset,
            "name": subset,
            "family": family,
            "families": [family, 'ftrack'],
        })
        self.log.info("collected instance: {}".format(instance.data))

        instance.data["files"] = list()
        instance.data['destination_list'] = list()
        instance.data['representations'] = list()

        for component in in_data['representations']:
            # instance.add(node)
            component['destination'] = component['files']
            collections, remainder = clique.assemble(component['files'])
            if collections:
                self.log.debug(collections)
                instance.data['startFrame'] = component['startFrame']
                instance.data['endFrame'] = component['endFrame']
                instance.data['frameRate'] = component['frameRate']

            instance.data["files"].append(component)
            instance.data["representations"].append(component)

            # "is_thumbnail": component['thumbnail'],
            # "is_preview": component['preview']

        self.log.info(in_data)
