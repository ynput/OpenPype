from pathlib import Path

import bpy

from openpype.hosts.blender.api import plugin


class ImportBlendLoader(plugin.AssetLoader):
    """Import action for Blender (unmanaged)

    Warning:
        The loaded content will be unmanaged and is *not* visible in the
        scene inventory. It's purely intended to merge content into your scene
        so you could also use it as a new base.

    """

    representations = ["blend"]
    families = ["*"]

    label = "Import"
    order = 10
    icon = "arrow-circle-down"
    color = "#775555"

    def load(self, context, name=None, namespace=None, data=None):
        scene = bpy.context.scene

        with bpy.data.libraries.load(self.fname) as (data_from, data_to):
            for attr in dir(data_to):
                setattr(data_to, attr, getattr(data_from, attr))

        # Add objects to current scene
        # for obj in data_to.objects:
        #     scene.collection.objects.link(obj)

        # We do not containerize imported content, it remains unmanaged
        return
