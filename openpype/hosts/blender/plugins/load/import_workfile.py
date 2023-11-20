import bpy

from openpype.hosts.blender.api import plugin


def append_workfile(context, fname, do_import):
    asset = context['asset']['name']
    subset = context['subset']['name']

    group_name = plugin.prepare_scene_name(asset, subset)

    # We need to preserve the original names of the scenes, otherwise,
    # if there are duplicate names in the current workfile, the imported
    # scenes will be renamed by Blender to avoid conflicts.
    original_scene_names = []

    with bpy.data.libraries.load(fname) as (data_from, data_to):
        for attr in dir(data_to):
            if attr == "scenes":
                for scene in data_from.scenes:
                    original_scene_names.append(scene)
            setattr(data_to, attr, getattr(data_from, attr))

    current_scene = bpy.context.scene

    for scene, s_name in zip(data_to.scenes, original_scene_names):
        scene.name = f"{group_name}_{s_name}"
        if do_import:
            collection = bpy.data.collections.new(f"{group_name}_{s_name}")
            for obj in scene.objects:
                collection.objects.link(obj)
            current_scene.collection.children.link(collection)
            for coll in scene.collection.children:
                collection.children.link(coll)


class AppendBlendLoader(plugin.AssetLoader):
    """Append workfile in Blender (unmanaged)

    Warning:
        The loaded content will be unmanaged and is *not* visible in the
        scene inventory. It's purely intended to merge content into your scene
        so you could also use it as a new base.
    """

    representations = ["blend"]
    families = ["workfile"]

    label = "Append Workfile"
    order = 9
    icon = "arrow-circle-down"
    color = "#775555"

    def load(self, context, name=None, namespace=None, data=None):
        path = self.filepath_from_context(context)
        append_workfile(context, path, False)

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
    families = ["workfile"]

    label = "Import Workfile"
    order = 9
    icon = "arrow-circle-down"
    color = "#775555"

    def load(self, context, name=None, namespace=None, data=None):
        path = self.filepath_from_context(context)
        append_workfile(context, path, True)

        # We do not containerize imported content, it remains unmanaged
        return
