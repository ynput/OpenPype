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
    data = dict()

    @staticmethod
    def get_collections() -> Generator:
        """Return all 'model' collections.

        Check if the family is 'model' and if it doesn't have the
        representation set. If the representation is set, it is a loaded model
        and we don't want to publish it.
        """
        for collection in bpy.context.scene.collection.children:
            if collection.get(AVALON_PROPERTY):
                if (
                        collection.get(AVALON_PROPERTY).get("id")
                        == "pyblish.avalon.instance"
                ):
                    yield collection

    def process(self, context):
        """Collect the models from the current Blender scene."""
        # get list of the collections with avalon properties in the scenes
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
            objects = list(collection.children)
            members = set()
            for obj in objects:
                objects.extend(list(obj.children))
                members.add(obj)

            # instance[:] = list(members)
            # self.log.debug(json.dumps(instance.data, indent=4))
            # for obj in instance:
            #     self.log.debug(obj)
            #
            # members = list(collection.objects)
            # if family == "animation":
            #     for obj in collection.objects:
            #         if obj.type == 'EMPTY' and obj.get(AVALON_PROPERTY):
            #             for child in obj.children:
            #                 if child.type == 'ARMATURE':
            #                     members.append(child)

            instance[:] = members
            self.log.debug(json.dumps(instance.data, indent=4))
            for obj in instance:
                self.log.debug(obj)
