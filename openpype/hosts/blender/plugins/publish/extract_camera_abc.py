import os

import bpy

from openpype.pipeline import publish
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


class ExtractCameraABC(publish.Extractor):
    """Extract camera as ABC."""

    label = "Extract Camera (ABC)"
    hosts = ["blender"]
    families = ["camera"]
    optional = True

    def process(self, instance):
        # Define extract output file path
        stagingdir = self.staging_dir(instance)
        filename = f"{instance.name}.abc"
        filepath = os.path.join(stagingdir, filename)

        context = bpy.context

        # Perform extraction
        self.log.info("Performing extraction..")

        plugin.deselect_all()

        selected = []
        active = None

        asset_group = None
        for obj in instance:
            if obj.get(AVALON_PROPERTY):
                asset_group = obj
                break
        assert asset_group, "No asset group found"

        # Need to cast to list because children is a tuple
        selected = list(asset_group.children)
        active = selected[0]

        for obj in selected:
            obj.select_set(True)

        context = plugin.create_blender_context(
            active=active, selected=selected)

        with bpy.context.temp_override(**context):
            # We export the abc
            bpy.ops.wm.alembic_export(
                filepath=filepath,
                selected=True,
                flatten=True
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
