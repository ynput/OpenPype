import json
from typing import Generator

import bpy

import pyblish.api
from openpype.pipeline import AVALON_INSTANCE_ID
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY
from openpype.hosts.blender.api.plugin import get_children_recursive


class CollectInstances(pyblish.api.ContextPlugin):
    """Gather instances and their data from avalone instance collections."""

    hosts = ["blender"]
    label = "Collect Instances"
    order = pyblish.api.CollectorOrder

    @staticmethod
    def get_collections() -> Generator:
        """Return all collections marked as OpenPype instance."""
        for collection in bpy.context.scene.collection.children:
            avalon_prop = collection.get(AVALON_PROPERTY) or dict()
            if avalon_prop.get("id") == AVALON_INSTANCE_ID:
                yield collection

    def process(self, context):
        """Collect instances from the current Blender scene."""
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
            members.update(set(get_children_recursive(collection)))
            members = list(members)
            members.append(collection)
            instance[:] = members
            self.log.debug(json.dumps(instance.data, indent=4))
            for obj in instance:
                self.log.debug(obj)
