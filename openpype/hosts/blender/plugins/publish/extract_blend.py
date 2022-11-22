import os

import bpy
from bson.objectid import ObjectId

from openpype.pipeline import (
    publish,
    discover_loader_plugins,
    AVALON_CONTAINER_ID,
)
from openpype.pipeline.load.utils import loaders_from_repre_context
from openpype.hosts.blender.api import plugin, get_compress_setting
from openpype.hosts.blender.api.pipeline import (
    metadata_update,
    AVALON_PROPERTY,
)


class ExtractBlend(publish.Extractor):
    """Extract the scene as blend file."""

    label = "Extract Blend"
    hosts = ["blender"]
    families = ["model", "camera", "rig", "action", "layout", "setdress"]
    optional = True

    pack_images = True

    def _get_loader_from_instance(self, instance):
        all_loaders = discover_loader_plugins()
        context = {
            "subset": {"schema": "openpype:container-2.0"},
            "version": {"data": {"families": [instance.data["family"]]}},
            "representation": {"name": "blend"},
        }
        loaders = loaders_from_repre_context(all_loaders, context)

        assert loaders, f"No loader modules found for {instance.name}"

        for loader_type in ("Instance", "Link", "Append"):
            for loader in loaders:
                if loader_type in loader.__name__:
                    return loader
        return loaders[0]

    def _get_images_from_objects(self, objects):
        """Get images from mesh objects materials."""
        # Get all objects materials using node tree shader.
        materials = set()
        for obj in objects:
            for mtl_slot in obj.material_slots:
                if (
                    mtl_slot.material
                    and mtl_slot.material.use_nodes
                    and mtl_slot.material.node_tree.type == "SHADER"
                ):
                    materials.add(mtl_slot.material)
        # Get ShaderNodeTexImage images from material node_tree.
        images = set()
        for material in materials:
            for node in material.node_tree.nodes:
                if (
                    isinstance(node, bpy.types.ShaderNodeTexImage)
                    and node.image
                ):
                    images.add(node.image)
        return images

    def process(self, instance):
        # Define extract output file path

        stagingdir = self.staging_dir(instance)
        filename = f"{instance.name}.blend"
        filepath = os.path.join(stagingdir, filename)

        # Perform extraction
        self.log.info("Performing extraction..")

        plugin.deselect_all()

        data_blocks = set()
        objects = set()

        # Adding all members of the instance to data blocks that will be
        # written into the blender library.
        for member in instance:
            data_blocks.add(member)
            # Get reference from override library.
            if member.override_library and member.override_library.reference:
                data_blocks.add(member.override_library.reference)
            # Store objects to pack images from their materials.
            if isinstance(member, bpy.types.Object):
                objects.add(member)

        # Store instance metadata
        instance_collection = instance[-1]
        instance_metadata = instance_collection[AVALON_PROPERTY].to_dict()
        instance_collection[AVALON_PROPERTY] = dict()

        # Create ID to allow blender import without using OP tools
        repre_id = str(ObjectId())

        # Get Loader module from instance
        loader_module = self._get_loader_from_instance(instance)

        # Add container metadata to collection
        metadata_update(
            instance_collection,
            {
                "schema": "openpype:container-2.0",
                "id": AVALON_CONTAINER_ID,
                "name": instance_metadata["subset"],
                "loader": loader_module.__name__,
                "representation": repre_id,
                "asset_name": instance_metadata["asset"],
                "parent": str(instance.data["assetEntity"]["parent"]),
                "family": instance.data["family"],
            },
        )

        # Pack used images in the blend files.
        packed_images = set()
        if self.pack_images:
            for image in self._get_images_from_objects(objects):
                if not image.packed_file and image.source != "GENERATED":
                    packed_images.add((image, image.is_dirty))
                    image.pack()

        bpy.data.libraries.write(
            filepath,
            data_blocks,
            path_remap="ABSOLUTE",
            fake_user=True,
            compress=get_compress_setting(),
        )

        # restor packed images.
        for image, is_dirty in packed_images:
            if not image.filepath:
                unpack_method = "REMOVE"
            elif is_dirty:
                unpack_method = "WRITE_ORIGINAL"
            else:
                unpack_method = "USE_ORIGINAL"
            image.unpack(method=unpack_method)

        # restor instance metadata
        instance_collection[AVALON_PROPERTY] = instance_metadata

        plugin.deselect_all()

        # Create representation dict
        representation = {
            "name": "blend",
            "ext": "blend",
            "files": filename,
            "stagingDir": stagingdir,
            "id": repre_id,
        }
        instance.data.setdefault("representations", [])
        instance.data["representations"].append(representation)

        self.log.info(
            f"Extracted instance '{instance.name}' to: {representation}"
        )
