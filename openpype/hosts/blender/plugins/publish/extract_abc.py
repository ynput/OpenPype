import os

import bpy

from openpype.pipeline import publish
from openpype.hosts.blender.api import plugin


class ExtractABC(publish.Extractor, publish.OptionalPyblishPluginMixin):
    """Extract as ABC."""

    label = "Extract ABC"
    hosts = ["blender"]
    families = ["pointcache"]

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        # Define extract output file path
        stagingdir = self.staging_dir(instance)
        asset_name = instance.data["assetEntity"]["name"]
        subset = instance.data["subset"]
        instance_name = f"{asset_name}_{subset}"
        filename = f"{instance_name}.abc"
        filepath = os.path.join(stagingdir, filename)

        # Perform extraction
        self.log.debug("Performing extraction..")

        plugin.deselect_all()

        asset_group = instance.data["transientData"]["instance_node"]

        selected = []
        for obj in instance:
            if isinstance(obj, bpy.types.Object):
                obj.select_set(True)
                selected.append(obj)

        context = plugin.create_blender_context(
            active=asset_group, selected=selected)

        with bpy.context.temp_override(**context):
            # We export the abc
            bpy.ops.wm.alembic_export(
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

        self.log.debug("Extracted instance '%s' to: %s",
                       instance.name, representation)


class ExtractModelABC(ExtractABC):
    """Extract model as ABC."""

    label = "Extract Model ABC"
    hosts = ["blender"]
    families = ["model"]
    optional = True
