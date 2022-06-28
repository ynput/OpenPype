from itertools import chain
import json
from typing import Generator

import bpy

import pyblish.api
from openpype.hosts.blender.api.utils import (
    BL_OUTLINER_TYPES,
    BL_TYPE_DATAPATH,
)
from openpype.pipeline import AVALON_CONTAINER_ID, AVALON_INSTANCE_ID
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


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
            if collection_id == AVALON_CONTAINER_ID:
                # Skip all collections of container
                children_to_skip.update(collection.children_recursive)
            elif collection_id == AVALON_INSTANCE_ID:
                # Match instance to publish
                yield collection

    def process(self, context):
        """Collect instances from the current Blender scene."""
        # Collect global scene data.
        context.data.update({
            "frameStart": bpy.context.scene.frame_start,
            "frameEnd": bpy.context.scene.frame_end,
            "fps": bpy.context.scene.render.fps,
        })

        # Create pyblish instances for scene instances
        for op_instance in bpy.context.scene.openpype_instances:
            datablocks = {
                datablock_ref.datablock
                for datablock_ref in op_instance.datablock_refs
            }

            # Remove if empty instance
            if not any(datablocks):
                bpy.context.scene.openpype_instances.remove(
                    bpy.context.scene.openpype_instances.find(op_instance.name)
                )
                continue

            # Create pyblish instance
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

            # Match publish checkbox
            instance.data["publish"] = op_instance.publish

            # Process datablocks
            members.update(datablocks)

            # Add datablocks used by the main datablocks
            non_outliner_datacols = set(
                chain.from_iterable(
                    getattr(bpy.data, datacol)
                    for bl_type, datacol in BL_TYPE_DATAPATH.items()
                    if bl_type not in BL_OUTLINER_TYPES
                )
            )
            members.update(
                {
                    d
                    for d, users in bpy.data.user_map(
                        subset=non_outliner_datacols
                    ).items()
                    if users & datablocks
                }
            )

            # Fill instance with members
            instance[:] = list(members)
            self.log.debug(json.dumps(instance.data, indent=4))
            for obj in instance:
                self.log.debug(obj)
