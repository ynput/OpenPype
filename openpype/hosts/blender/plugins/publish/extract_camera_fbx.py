import os

import bpy

from openpype.pipeline import publish
from openpype.hosts.blender.api import plugin


class ExtractCamera(publish.Extractor, publish.OptionalPyblishPluginMixin):
    """Extract as the camera as FBX."""

    label = "Extract Camera (FBX)"
    hosts = ["blender"]
    families = ["camera"]
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        # Define extract output file path
        stagingdir = self.staging_dir(instance)
        asset_name = instance.data["assetEntity"]["name"]
        subset = instance.data["subset"]
        instance_name = f"{asset_name}_{subset}"
        filename = f"{instance_name}.fbx"
        filepath = os.path.join(stagingdir, filename)

        # Perform extraction
        self.log.debug("Performing extraction..")

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

        with bpy.context.temp_override(**context):
            # We export the fbx
            bpy.ops.export_scene.fbx(
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

        self.log.debug("Extracted instance '%s' to: %s",
                       instance.name, representation)
