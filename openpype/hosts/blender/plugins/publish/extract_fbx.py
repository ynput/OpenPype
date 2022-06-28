import os

import bpy

from openpype.pipeline import publish
from openpype.pipeline import legacy_io
from openpype.hosts.blender.api import plugin


class ExtractFBX(publish.Extractor):
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

        # Get project settings
        project_settings = api.get_project_settings(
            legacy_io.Session["AVALON_PROJECT"]
        )
        scale_length = (
            project_settings
            ["blender"]
            ["publish"]
            ["ExtractFBX"]
            ["scale_length"]
        )

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

        context = plugin.create_blender_context(
            active=selected[-1], selected=selected
        )

        kept_scale_length = bpy.context.scene.unit_settings.scale_length
        if scale_length > 0:
            bpy.context.scene.unit_settings.scale_length = scale_length

        # We export the fbx
        bpy.ops.export_scene.fbx(
            context,
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
