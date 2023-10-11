import json
from itertools import chain
from typing import Generator

import bpy

import pyblish.api
from openpype.hosts.blender.api.pipeline import (
    AVALON_INSTANCES,
    AVALON_PROPERTY,
)


class CollectInstances(pyblish.api.ContextPlugin):
    """Collect the data of a model."""

    hosts = ["blender"]
    label = "Collect Instances"
    order = pyblish.api.CollectorOrder

    @staticmethod
    def get_asset_groups() -> Generator:
        """Return all instances that are empty objects asset groups.
        """
        instances = bpy.data.collections.get(AVALON_INSTANCES)
        for obj in instances.objects:
            avalon_prop = obj.get(AVALON_PROPERTY) or {}
            if avalon_prop.get('id') == 'pyblish.avalon.instance':
                yield obj

    @staticmethod
    def get_collections() -> Generator:
        """Return all instances that are collections.
        """
        instances = bpy.data.collections.get(AVALON_INSTANCES)
        for collection in instances.children:
            avalon_prop = collection.get(AVALON_PROPERTY) or {}
            if avalon_prop.get('id') == 'pyblish.avalon.instance':
                yield collection

    @staticmethod
    def create_instance(context, group):
        avalon_prop = group[AVALON_PROPERTY]
        asset = avalon_prop['asset']
        family = avalon_prop['family']
        subset = avalon_prop['subset']
        task = avalon_prop['task']
        name = f"{asset}_{subset}"
        return context.create_instance(
            name=name,
            family=family,
            families=[family],
            subset=subset,
            asset=asset,
            task=task,
        )

    def process(self, context):
        """Collect the models from the current Blender scene."""
        asset_groups = self.get_asset_groups()
        collections = self.get_collections()

        instances = chain(asset_groups, collections)

        for group in instances:
            instance = self.create_instance(context, group)
            family = instance.data["family"]
            members = []
            if type(group) == bpy.types.Collection:
                members = list(group.objects)
                if family == "animation":
                    for obj in group.objects:
                        if obj.type == 'EMPTY' and obj.get(AVALON_PROPERTY):
                            members.extend(
                                child for child in obj.children
                                if child.type == 'ARMATURE')
            else:
                members = group.children_recursive

            if family == "pointcache":
                instance.data["families"].append("abc.export")

            members.append(group)
            instance[:] = members
            self.log.debug(json.dumps(instance.data, indent=4))
            for obj in instance:
                self.log.debug(obj)
