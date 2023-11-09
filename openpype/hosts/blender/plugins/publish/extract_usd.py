import os

import bpy

from openpype.pipeline import publish
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


class ExtractUSD(publish.Extractor):
    """Extract as USD."""

    label = "Extract USD"
    hosts = ["blender"]
    families = ["usd"]

    def process(self, instance):
        # Define extract output file path
        stagingdir = self.staging_dir(instance)
        filename = f"{instance.name}.usd"
        filepath = os.path.join(stagingdir, filename)

        # Perform extraction
        self.log.debug("Performing extraction..")

        # Select all members to "export selected"
        plugin.deselect_all()
        selected = []
        asset_group = None
        for obj in instance:
            if isinstance(obj, bpy.types.Collection):
                # TODO: instead include all children - but that's actually
                #   up to the Collector instead
                continue

            obj.select_set(True)
            selected.append(obj)
            if obj.get(AVALON_PROPERTY):
                asset_group = obj

        context = plugin.create_blender_context(
            active=asset_group, selected=selected)

        # Export USD
        bpy.ops.wm.usd_export(
            context,
            filepath=filepath,
            selected_objects_only=True,
            export_textures=False,
            relative_paths=False,
            export_animation=False,
            export_hair=False,
            export_uvmaps=True,
            # TODO: add for new version of Blender (4+?)
            #export_mesh_colors=True,
            export_normals=True,
            export_materials=True,
            use_instancing=True
        )

        plugin.deselect_all()

        # Add representation
        representation = {
            'name': 'usd',
            'ext': 'usd',
            'files': filename,
            "stagingDir": stagingdir,
        }
        instance.data.setdefault("representations", []).append(representation)
        self.log.debug("Extracted instance '%s' to: %s",
                       instance.name, representation)
