import os

import bpy

from openpype import api
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


class ExtractABC(api.Extractor):
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

        context = bpy.context
        scene = context.scene
        view_layer = context.view_layer

        # Perform extraction
        self.log.info("Performing extraction..")

        plugin.deselect_all()

        selected = []
        asset_group = None

        for obj in instance:
            obj.select_set(True)
            selected.append(obj)
            if obj.get(AVALON_PROPERTY):
                asset_group = obj

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
