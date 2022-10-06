import os

import bpy

from openpype.pipeline import publish
from openpype.hosts.blender.api import plugin


class ExtractFBX(publish.Extractor):
    """Extract as FBX."""

    label = "Extract FBX"
    hosts = ["blender"]
    families = ["model", "rig"]
    optional = True

    scale_length = 0

    def process(self, instance):
        # Define extract output file path
        stagingdir = self.staging_dir(instance)
        filename = f"{instance.name}.fbx"
        filepath = os.path.join(stagingdir, filename)

        # Perform extraction
        self.log.info("Performing extraction..")

        plugin.deselect_all()

        selected = []

        for obj in instance:
            if isinstance(obj, bpy.types.Object):
                obj.select_set(True)
                selected.append(obj)

        new_materials = []
        new_materials_objs = []

        for obj in selected:
            if obj.type == 'MESH' and len(obj.data.materials) == 0:
                mat = bpy.data.materials.new(obj.name)
                obj.data.materials.append(mat)
                new_materials.append(mat)
                new_materials_objs.append(obj)

        kept_scale_length = bpy.context.scene.unit_settings.scale_length
        if self.scale_length > 0:
            bpy.context.scene.unit_settings.scale_length = self.scale_length

        # We export the fbx
        with plugin.context_override(active=selected[-1], selected=selected):
            bpy.ops.export_scene.fbx(
                filepath=filepath,
                use_active_collection=False,
                use_selection=True,
                mesh_smooth_type='FACE',
                add_leaf_bones=False
            )

        bpy.context.scene.unit_settings.scale_length = kept_scale_length

        plugin.deselect_all()

        for mat in new_materials:
            bpy.data.materials.remove(mat)

        for obj in new_materials_objs:
            obj.data.materials.pop()

        instance.data.setdefault("representations", [])

        representation = {
            'name': 'fbx',
            'ext': 'fbx',
            'files': filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(representation)

        self.log.info(
            f"Extracted instance '{instance.name}' to: {representation}"
        )
