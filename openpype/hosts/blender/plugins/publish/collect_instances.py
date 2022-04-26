import json
from typing import Generator

import bpy

import pyblish.api
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


class CollectInstances(pyblish.api.ContextPlugin):
    """Collect the data of a model."""

    hosts = ["blender"]
    label = "Collect Instances"
    order = pyblish.api.CollectorOrder

    @staticmethod
    def get_collections() -> Generator:
        """Return all 'model' collections.

        Check if the family is 'model' and if it doesn't have the
        representation set. If the representation is set, it is a loaded model
        and we don't want to publish it.
        """
        for collection in bpy.context.scene.collection.children:
            avalon_prop = collection.get(AVALON_PROPERTY) or dict()
            if avalon_prop.get('id') == 'pyblish.avalon.instance':
                yield collection

    def process(self, context):
        """Collect the models from the current Blender scene."""
        collections = self.get_collections()

        for collection in collections:
            avalon_prop = collection[AVALON_PROPERTY]
            asset = avalon_prop["asset"]
            family = avalon_prop["family"]
            subset = avalon_prop["subset"]
            task = avalon_prop["task"]
            name = collection.name
            instance = context.create_instance(
                name=name,
                family=family,
                families=[family],
                subset=subset,
                asset=asset,
                task=task,
            )
            # collect all members recursively
            collection_childs = list(collection.children)
            members = set(collection.objects)
            for child in collection_childs:
                collection_childs.extend(list(child.children))
                members.update(list(child.objects))
            objects = list(members)
            for obj in objects:
                objects.extend(list(obj.children))
                members.add(obj)
            # append the collection to members and update intances list
            members.add(collection)
            instance[:] = list(members)
            self.log.debug(json.dumps(instance.data, indent=4))
            for obj in instance:
                self.log.debug(obj)
