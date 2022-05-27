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
        """Return all collections marked as OpenPype "instance".

        The property `bpy.context.scene.openpype_instances` keeps
        track of the collections created as OP instances for the current scene.
        """
        instance_collections = {
            bpy.data.collections.get(instance.collection_name)
            for instance in bpy.context.scene.openpype_instances
        }
        for collection in instance_collections:
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
            # collect all objects recursively
            members = set()
            objects = list(collection.all_objects)
            for obj in objects:
                objects.extend(list(obj.children))
                members.add(obj)
            # append the collections to members and update intances list
            members.update(set(collection.children_recursive))
            members.add(collection)
            instance[:] = list(members)
            self.log.debug(json.dumps(instance.data, indent=4))
            for obj in instance:
                self.log.debug(obj)
