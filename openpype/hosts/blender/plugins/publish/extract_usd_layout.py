import os

import bpy

from pxr import Sdf, Usd, UsdGeom

from avalon import blender, io
import openpype.api


class ExtractUsdLayout(openpype.api.Extractor):
    """Extract a Usd layout."""

    label = "Extract Usd Layout"
    hosts = ["blender"]
    families = ["layout"]
    optional = True

    def process(self, instance):
        # Define extract output file path
        stagingdir = self.staging_dir(instance)

        # Perform extraction
        self.log.info("Performing extraction..")

        filename = f"{instance.name}.usda"
        path = os.path.join(stagingdir, filename)

        stage_ref = Usd.Stage.CreateNew(path)

        for collection in instance:
            collection_path = Sdf.Path(f"/{collection.name}")
            self.log.debug(f"collection_path: {collection_path}")
            stage_ref.DefinePrim(collection_path)
            for asset_collection in collection.children:
                asset_path = Sdf.Path(
                    f"/{collection.name}/{asset_collection.name}")
                self.log.debug(f"asset_path: {asset_path}")
                asset_ref = stage_ref.DefinePrim(asset_path)

                container = bpy.data.collections[
                    asset_collection.name + '_CON']
                metadata = container.get(blender.pipeline.AVALON_PROPERTY)

                parent = metadata["parent"]
                family = metadata["family"]

                self.log.debug("Parent: {}".format(parent))
                blend = io.find_one(
                    {
                        "type": "representation",
                        "parent": io.ObjectId(parent),
                        "name": "blend"
                    },
                    projection={"_id": True})
                blend_id = blend["_id"]

                # A current limitation in the API makes it impossible to
                # list the references, so it cannot be parsed when loading.
                # It can only be accessed with an Asset Resolver.
                # For now, the representation is saved as a custom string.
                #
                # asset_ref.GetReferences().AddReference(str(blend_id))
                asset_ref.CreateAttribute(
                    'reference', Sdf.ValueTypeNames.String).Set(str(blend_id))

                asset_ref.CreateAttribute(
                    'family', Sdf.ValueTypeNames.String).Set(family)
                asset_ref.CreateAttribute(
                    'instance_name', Sdf.ValueTypeNames.String).Set(
                        asset_collection.name)
                asset_ref.CreateAttribute(
                    'asset_name', Sdf.ValueTypeNames.String).Set(
                        metadata["lib_container"])
                asset_ref.CreateAttribute(
                    'file_path', Sdf.ValueTypeNames.String).Set(
                        metadata["libpath"])

                obj = asset_collection.objects[0]

                geometry = UsdGeom.Xform.Define(stage_ref, asset_path)
                geometry.AddTranslateOp().Set(value=(
                    obj.location.x,
                    obj.location.y,
                    obj.location.z))
                geometry.AddRotateXYZOp().Set(value=(
                    obj.rotation_euler.x,
                    obj.rotation_euler.y,
                    obj.rotation_euler.z))
                geometry.AddScaleOp().Set(value=(
                    obj.scale.x,
                    obj.scale.y,
                    obj.scale.z))

        stage_ref.Save()

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'usd',
            'ext': 'usd',
            'files': filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '%s' to: %s",
                      instance.name, representation)
