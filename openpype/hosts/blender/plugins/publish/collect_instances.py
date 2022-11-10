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
        for collection in bpy.context.scene.collection.children_recursive:
            avalon_prop = collection.get(AVALON_PROPERTY) or dict()
            if avalon_prop.get("id") == AVALON_INSTANCE_ID:
                yield collection

    def process(self, context):
        """Collect instances from the current Blender scene."""
        members = set()

        if True:  # TODO setting | Instances are PropertyGroups
            instances = list(bpy.context.scene.openpype_instances)

            # Process datablocks
            for op_instance in bpy.context.scene.openpype_instances:
                members.update(
                    {
                        eval(datablock_ref.datapath).get(datablock_ref.name)
                        for datablock_ref in op_instance.datablocks
                    }
                )
        else:  # Instances are collections
            instances = self.get_collections()

        for op_instance in instances:
            avalon_prop = op_instance[AVALON_PROPERTY]
            instance = context.create_instance(
                name=op_instance.name,
                family=avalon_prop["family"],
                families=[avalon_prop["family"]],
                subset=avalon_prop["subset"],
                asset=avalon_prop["asset"],
                task=avalon_prop["task"],
            )

            # If outliner data
            instance_collection = bpy.data.collections.get(op_instance.name)
            if instance_collection:
                # collect all objects recursively
                objects = list(instance_collection.all_objects)
                for obj in objects:
                    objects.extend(list(obj.children))
                    members.add(obj)
                # append the collections to members and update intances list
                members.update(
                    set(get_children_recursive(instance_collection))
                )

            instance[:] = members
            self.log.debug(json.dumps(instance.data, indent=4))
            for obj in instance:
                self.log.debug(obj)
