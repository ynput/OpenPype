import os

import bpy

from openpype.pipeline import publish
from openpype.hosts.blender.api import plugin


class ExtractABC(publish.Extractor):
    """Extract as ABC."""

    label = "Extract ABC"
    hosts = ["blender"]
    families = ["model", "pointcache"]
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

        for obj in instance:
            if isinstance(obj, bpy.types.Object):
                obj.select_set(True)
                selected.append(obj)

        context = plugin.create_blender_context(
            active=selected[-1], selected=selected
        )

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

        self.log.info(
            f"Extracted instance '{instance.name}' to: {representation}"
        )
