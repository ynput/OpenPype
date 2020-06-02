import os

import pype.api
import pype.hosts.blender.plugin

import bpy


class ExtractABC(pype.api.Extractor):
    """Extract as ABC."""

    label = "Extract ABC"
    hosts = ["blender"]
    families = ["model"]
    optional = True

    def process(self, instance):
        # Define extract output file path

        stagingdir = self.staging_dir(instance)
        filename = f"{instance.name}.fbx"
        filepath = os.path.join(stagingdir, filename)

        context = bpy.context
        scene = context.scene
        view_layer = context.view_layer

        # Perform extraction
        self.log.info("Performing extraction..")

        collections = [
            obj for obj in instance if type(obj) is bpy.types.Collection]

        assert len(collections) == 1, "There should be one and only one " \
            "collection collected for this asset"

        old_active_layer_collection = view_layer.active_layer_collection

        layers = view_layer.layer_collection.children

        # Get the layer collection from the collection we need to export.
        # This is needed because in Blender you can only set the active
        # collection with the layer collection, and there is no way to get
        # the layer collection from the collection
        # (but there is the vice versa).
        layer_collections = [
            layer for layer in layers if layer.collection == collections[0]]

        assert len(layer_collections) == 1

        view_layer.active_layer_collection = layer_collections[0]

        old_scale = scene.unit_settings.scale_length

        selected = list()

        for obj in instance:
            try:
                obj.select_set(True)
                selected.append(obj)
            except:
                continue

        new_context = pype.hosts.blender.plugin.create_blender_context(active=selected[0], selected=selected)

        # We set the scale of the scene for the export
        scene.unit_settings.scale_length = 0.01

        self.log.info(new_context)

        # We export the abc
        bpy.ops.wm.alembic_export(
            new_context,
            filepath=filepath,
            start=1,
            end=1
        )

        view_layer.active_layer_collection = old_active_layer_collection

        scene.unit_settings.scale_length = old_scale

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
