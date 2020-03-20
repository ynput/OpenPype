from typing import Generator

import bpy

import pyblish.api
from avalon.blender.pipeline import AVALON_PROPERTY


class CollectRig(pyblish.api.ContextPlugin):
    """Collect the data of a rig."""

    hosts = ["blender"]
    label = "Collect Rig"
    order = pyblish.api.CollectorOrder

    @staticmethod
    def get_rig_collections() -> Generator:
        """Return all 'rig' collections.

        Check if the family is 'rig' and if it doesn't have the
        representation set. If the representation is set, it is a loaded rig
        and we don't want to publish it.
        """
        for collection in bpy.data.collections:
            avalon_prop = collection.get(AVALON_PROPERTY) or dict()
            if (avalon_prop.get('family') == 'rig' and
                    not avalon_prop.get('representation')):
                yield collection

    def process(self, context):
        """Collect the rigs from the current Blender scene."""
        collections = self.get_rig_collections()
        for collection in collections:
            avalon_prop = collection[AVALON_PROPERTY]
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
            members = list(collection.objects)
            members.append(collection)
            instance[:] = members
            self.log.debug(instance.data)
