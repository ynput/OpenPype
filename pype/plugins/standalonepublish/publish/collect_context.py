import os
import pyblish.api
from avalon import (
    io,
    api as avalon
)
import json
import logging


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
        json_path = os.environ.get("SAPUBLISH_INPATH")
        with open(json_path, "r") as f:
            in_data = json.load(f)

        context.data["stagingDir"] = os.path.dirname(json_path)
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
        context.data['family'] = family
        context.data['subset'] = subset

        instances = []

        for component in in_data['representations']:
            instance = context.create_instance(subset)
            # instance.add(node)

            instance.data.update({
                "subset": subset,
                "asset": asset_name,
                "label": component['label'],
                "name": component['representation'],
                "subset": subset,
                "family": family,
                "is_thumbnail": component['thumbnail'],
                "is_preview": component['preview']
            })

            self.log.info("collected instance: {}".format(instance.data))
            instances.append(instance)

        context.data["instances"] = instances
        self.log.info(in_data)
