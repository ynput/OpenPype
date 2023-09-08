import os

import bpy

from openpype.pipeline import publish
from openpype.hosts.blender.api import plugin


class ExtractAnimationABC(publish.Extractor):
    """Extract as ABC."""

    label = "Extract Animation ABC"
    hosts = ["blender"]
    families = ["animation"]
    optional = True

    def process(self, instance):
        # Define extract output file path
        stagingdir = self.staging_dir(instance)
        filename = f"{instance.name}.abc"
        filepath = os.path.join(stagingdir, filename)

        # Perform extraction
        self.log.info("Performing extraction..")

        plugin.deselect_all()

        selected = []
        asset_group = None

        objects = []
        for obj in instance:
            if isinstance(obj, bpy.types.Collection):
                for child in obj.all_objects:
                    objects.append(child)
        for obj in objects:
            children = [o for o in bpy.data.objects if o.parent == obj]
            for child in children:
                objects.append(child)

        for obj in objects:
            obj.select_set(True)
            selected.append(obj)

        context = plugin.create_blender_context(
            active=asset_group, selected=selected)

        # We export the abc
        bpy.ops.wm.alembic_export(
            context,
            filepath=filepath,
            selected=True,
            flatten=False
        )

        plugin.deselect_all()

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'abc',
            'ext': 'abc',
            'files': filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '%s' to: %s",
                      instance.name, representation)
