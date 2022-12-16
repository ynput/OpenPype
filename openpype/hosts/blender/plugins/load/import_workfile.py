import bpy

from openpype.hosts.blender.api import plugin


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
    order = 10
    icon = "arrow-circle-down"
    color = "#775555"

    def load(self, context, name=None, namespace=None, data=None):
        with bpy.data.libraries.load(self.fname) as (data_from, data_to):
            for attr in dir(data_to):
                setattr(data_to, attr, getattr(data_from, attr))

        # Add objects to current scene
        # scene = bpy.context.scene
        # for obj in data_to.objects:
        #     scene.collection.objects.link(obj)

        # We do not containerize imported content, it remains unmanaged
        return
