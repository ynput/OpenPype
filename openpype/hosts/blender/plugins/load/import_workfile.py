from pathlib import Path

import bpy

from openpype.hosts.blender.api import plugin


def get_unique_number(asset, subset):
    count = 1
    name = f"{asset}_{count:0>2}_{subset}"
    collection_names = [coll.name for coll in bpy.data.collections]
    while name in collection_names:
        count += 1
        name = f"{asset}_{count:0>2}_{subset}"
    return f"{count:0>2}"


class AppendBlendLoader(plugin.AssetLoader):
    """Append workfile in Blender (unmanaged)

    Warning:
        The loaded content will be unmanaged and is *not* visible in the
        scene inventory. It's purely intended to merge content into your scene
        so you could also use it as a new base.
    """

    representations = ["blend"]
    families = ["*"]

    label = "Append Workfile"
    order = 9
    icon = "arrow-circle-down"
    color = "#775555"

    def load(self, context, name=None, namespace=None, data=None):
        with bpy.data.libraries.load(self.fname) as (data_from, data_to):
            for attr in dir(data_to):
                setattr(data_to, attr, getattr(data_from, attr))

        # We do not containerize imported content, it remains unmanaged
        return


class ImportBlendLoader(plugin.AssetLoader):
    """Import workfile in the current Blender scene (unmanaged)

    Warning:
        The loaded content will be unmanaged and is *not* visible in the
        scene inventory. It's purely intended to merge content into your scene
        so you could also use it as a new base.
    """

    representations = ["blend"]
    families = ["*"]

    label = "Import Workfile"
    order = 9
    icon = "arrow-circle-down"
    color = "#775555"

    def load(self, context, name=None, namespace=None, data=None):
        asset = context['asset']['name']
        subset = context['subset']['name']

        unique_number = get_unique_number(asset, subset)
        group_name = plugin.asset_name(asset, subset, unique_number)

        with bpy.data.libraries.load(self.fname) as (data_from, data_to):
            for attr in dir(data_to):
                setattr(data_to, attr, getattr(data_from, attr))

        current_scene = bpy.context.scene

        for scene in data_to.scenes:
            # scene.name = group_name
            collection = bpy.data.collections.new(name=group_name)
            for obj in scene.objects:
                collection.objects.link(obj)
            current_scene.collection.children.link(collection)
            for coll in scene.collection.children:
                collection.children.link(coll)

        # We do not containerize imported content, it remains unmanaged
        return
