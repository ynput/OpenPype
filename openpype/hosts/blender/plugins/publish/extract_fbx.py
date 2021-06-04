import os

from openpype import api
from openpype.hosts.blender.api import plugin
from avalon.blender.pipeline import AVALON_PROPERTY

import bpy


class ExtractFBX(api.Extractor):
    """Extract as FBX."""

    label = "Extract FBX"
    hosts = ["blender"]
    families = ["model", "rig"]
    optional = True

    def process(self, instance):
        # Define extract output file path
        stagingdir = self.staging_dir(instance)
        filename = f"{instance.name}.fbx"
        filepath = os.path.join(stagingdir, filename)

        scene = bpy.context.scene

        # Perform extraction
        self.log.info("Performing extraction..")

        bpy.ops.object.select_all(action='DESELECT')

        selected = []
        asset_group = None

        for obj in instance:
            obj.select_set(True)
            selected.append(obj)
            if obj.get(AVALON_PROPERTY):
                asset_group = obj

        context = plugin.create_blender_context(
            active=asset_group, selected=selected)

        new_materials = []

        for obj in collections[0].all_objects:
            if obj.type == 'MESH':
                mat = bpy.data.materials.new(obj.name)
                obj.data.materials.append(mat)
                new_materials.append(mat)

        # We export the fbx
        bpy.ops.export_scene.fbx(
            context,
            filepath=filepath,
            use_active_collection=False,
            use_selection=True,
            mesh_smooth_type='FACE',
            add_leaf_bones=False
        )

        bpy.ops.object.select_all(action='DESELECT')

        for mat in new_materials:
            bpy.data.materials.remove(mat)

        for obj in collections[0].all_objects:
            if obj.type == 'MESH':
                obj.data.materials.pop()

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'fbx',
            'ext': 'fbx',
            'files': filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '%s' to: %s",
                      instance.name, representation)
