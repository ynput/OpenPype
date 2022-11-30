import json
from typing import Generator

import bpy

import pyblish.api
from openpype.pipeline import AVALON_CONTAINER_ID, AVALON_INSTANCE_ID
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY
from openpype.hosts.blender.api.plugin import get_children_recursive


class CollectInstances(pyblish.api.ContextPlugin):
    """Gather instances and their data from avalone instance collections."""

    hosts = ["blender"]
    label = "Collect Instances"
    order = pyblish.api.CollectorOrder

    @staticmethod
    def get_collections() -> Generator:
        """Return all collections marked as OpenPype instance.

        When a container embeds instances they must be skipped.
        """
        children_to_skip = set()
        for collection in bpy.context.scene.collection.children_recursive:
            if collection in children_to_skip:
                continue

            collection_id = collection.get(AVALON_PROPERTY, {}).get("id")
            if (
                collection_id == AVALON_CONTAINER_ID
            ):  # Skip all collections of container
                children_to_skip.update(collection.children_recursive)
            elif (
                collection_id == AVALON_INSTANCE_ID
            ):  # Match instance to publish
                yield collection

    def process(self, context):
        """Collect instances from the current Blender scene."""
        instances = set()

        # PropertyGroups instances
        if hasattr(bpy.context.scene, "openpype_instances"):
            instances.update(bpy.context.scene.openpype_instances)

        # Collections instances
        instances.update(
            {
                collection
                for collection in self.get_collections()
                if collection.name
                not in {
                    inst.name for inst in bpy.context.scene.openpype_instances
                }
            }
        )

        for op_instance in instances:
            members = set()

            avalon_prop = op_instance[AVALON_PROPERTY]
            instance = context.create_instance(
                name=op_instance.name,
                family=avalon_prop["family"],
                families=[avalon_prop["family"]],
                subset=avalon_prop["subset"],
                asset=avalon_prop["asset"],
                task=avalon_prop["task"],
            )

            # Process datablocks
            if hasattr(op_instance, "datablocks"):
                members.update(
                    {
                        eval(datablock_ref.datapath).get(datablock_ref.name)
                        for datablock_ref in op_instance.datablocks
                    }
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

            # Add instance holder as first item
            members = list(members)
            members.insert(0, op_instance)

            instance[:] = members
            self.log.debug(json.dumps(instance.data, indent=4))
            for obj in instance:
                self.log.debug(obj)
