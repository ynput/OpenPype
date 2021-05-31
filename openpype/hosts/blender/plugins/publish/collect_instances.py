from typing import Generator

import bpy
import json

import pyblish.api
from avalon.blender.pipeline import AVALON_PROPERTY
from avalon.blender.pipeline import AVALON_INSTANCES


class CollectInstances(pyblish.api.ContextPlugin):
    """Collect the data of a model."""

    hosts = ["blender"]
    label = "Collect Instances"
    order = pyblish.api.CollectorOrder

    @staticmethod
    def get_asset_groups() -> Generator:
        """Return all 'model' collections.

        Check if the family is 'model' and if it doesn't have the
        representation set. If the representation is set, it is a loaded model
        and we don't want to publish it.
        """
        instances = bpy.data.collections.get(AVALON_INSTANCES)
        for obj in instances.objects:
            avalon_prop = obj.get(AVALON_PROPERTY) or dict()
            if avalon_prop.get('id') == 'pyblish.avalon.instance':
                yield obj

    def process(self, context):
        """Collect the models from the current Blender scene."""
        asset_groups = self.get_asset_groups()

        for group in asset_groups:
            avalon_prop = group[AVALON_PROPERTY]
            asset = avalon_prop['asset']
            family = avalon_prop['family']
            subset = avalon_prop['subset']
            task = avalon_prop['task']
            name = f"{asset}_{subset}"
            instance = context.create_instance(
                name=name,
                family=family,
                families=[family],
                subset=subset,
                asset=asset,
                task=task,
            )
            objects = list(group.children)
            members = set()
            for obj in objects:
                objects.extend(list(obj.children))
                members.add(obj)
            members.add(group)
            instance[:] = list(members)
            self.log.debug(json.dumps(instance.data, indent=4))
            for obj in instance:
                self.log.debug(obj)
