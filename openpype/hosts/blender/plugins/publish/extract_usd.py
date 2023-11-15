import os

import bpy

from openpype.pipeline import publish
from openpype.hosts.blender.api import plugin, lib


class ExtractUSD(publish.Extractor):
    """Extract as USD."""

    label = "Extract USD"
    hosts = ["blender"]
    families = ["usd"]

    def process(self, instance):

        # Ignore runtime instances (e.g. USD layers)
        # TODO: This is better done via more specific `families`
        if not instance.data.get("transientData", {}).get("instance_node"):
            return

        # Define extract output file path
        stagingdir = self.staging_dir(instance)
        filename = f"{instance.name}.usd"
        filepath = os.path.join(stagingdir, filename)

        # Perform extraction
        self.log.debug("Performing extraction..")

        # Select all members to "export selected"
        plugin.deselect_all()

        selected = []
        for obj in instance:
            if isinstance(obj, bpy.types.Object):
                obj.select_set(True)
                selected.append(obj)

        root = lib.get_highest_root(objects=instance[:])
        if not root:
            instance_node = instance.data["transientData"]["instance_node"]
            raise publish.KnownPublishError(
                f"No root object found in instance: {instance_node.name}"
            )
        self.log.debug(f"Exporting using active root: {root.name}")

        context = plugin.create_blender_context(
            active=root, selected=selected)

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
