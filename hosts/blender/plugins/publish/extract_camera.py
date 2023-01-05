import os

import bpy

from openpype import api
from openpype.hosts.blender.api import plugin


class ExtractCamera(api.Extractor):
    """Extract as the camera as FBX."""

    label = "Extract Camera"
    hosts = ["blender"]
    families = ["camera"]
    optional = True

    def process(self, instance):
        # Define extract output file path
        stagingdir = self.staging_dir(instance)
        filename = f"{instance.name}.fbx"
        filepath = os.path.join(stagingdir, filename)

        # Perform extraction
        self.log.info("Performing extraction..")

        plugin.deselect_all()

        selected = []

        camera = None

        for obj in instance:
            if obj.type == "CAMERA":
                obj.select_set(True)
                selected.append(obj)
                camera = obj
                break

        assert camera, "No camera found"

        context = plugin.create_blender_context(
            active=camera, selected=selected)

        scale_length = bpy.context.scene.unit_settings.scale_length
        bpy.context.scene.unit_settings.scale_length = 0.01

        # We export the fbx
        bpy.ops.export_scene.fbx(
            context,
            filepath=filepath,
            use_active_collection=False,
            use_selection=True,
            bake_anim_use_nla_strips=False,
            bake_anim_use_all_actions=False,
            add_leaf_bones=False,
            armature_nodetype='ROOT',
            object_types={'CAMERA'},
            bake_anim_simplify_factor=0.0
        )

        bpy.context.scene.unit_settings.scale_length = scale_length

        plugin.deselect_all()

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
