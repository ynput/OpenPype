import os
from pathlib import Path
from typing import List, Set, Tuple

import bpy

import openpype.api
from openpype.pipeline import legacy_io


class ExtractBlendLook(openpype.api.Extractor):
    """Extract a blend file with materials and meshes."""

    label = "Extract Look"
    hosts = ["blender"]
    families = ["look"]
    optional = True

    pack_images = True

    @staticmethod
    def _get_images_from_materials(materials):
        """Get images from materials."""
        # Get ShaderNodeTexImage from material with node_tree.
        images = set()
        for material in materials:
            if material.use_nodes and material.node_tree.type == "SHADER":
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
        filename = f"{instance.name}.mat.blend"
        filepath = os.path.join(stagingdir, filename)

        # Perform extraction
        self.log.info("Performing extraction...")

        data_blocks = set()
        objects = set()
        collection = instance[-1]

        for obj in instance:
            # Store objects to pack images from their materials.
            if isinstance(obj, bpy.types.Object) and obj.type == "MESH":
                objects.add(obj)
                data_blocks.add(obj)

        # Get all objects materials.
        materials = set()
        materials_assignment = dict()
        materials_indexes = dict()
        for obj in objects:
            if len(obj.material_slots):
                obj_materials = list()
                for mtl_slot in obj.material_slots:
                    material = mtl_slot.material
                    if material:
                        material.use_fake_user = True
                        materials.add(material)
                        data_blocks.add(material)
                    obj_materials.append(material)

                materials_assignment[obj.name] = obj_materials

                # Get polygons material indexes for objects.
                if len(obj_materials) > 1:
                    materials_indexes[obj.name] = [
                        face.material_index for face in obj.data.polygons
                    ]

        data_blocks.update({*bpy.data.textures, *bpy.data.node_groups})

        # Store materials assignment and indexes informations.
        collection["materials_assignment"] = materials_assignment
        collection["materials_indexes"] = materials_indexes

        # Get images and process resources
        images = self._get_images_from_materials(materials)
        transfers, hashes, remapped = self._process_resources(instance, images)

        data_blocks.add(collection)

        bpy.data.libraries.write(filepath, data_blocks)

        # Restore remapped path
        for image, sourcepath in remapped:
            image.filepath = sourcepath.as_posix()

        collection.pop("materials_assignment")
        collection.pop("materials_indexes")

        for material in materials:
            material.use_fake_user = False

        instance.data.setdefault("representations", [])

        representation = {
            "name": "blend",
            "ext": "blend",
            "files": filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(representation)

        # Set up the resources transfers/links for the integrator
        instance.data.setdefault("transfers", [])
        instance.data["transfers"].extend(transfers)

        # Source hash for the textures
        instance.data["sourceHashes"] = hashes

        self.log.info(
            f"Extracted instance '{instance.name}' to: {representation}"
        )

    def _process_resources(
        self, instance: dict, images: set
    ) -> Tuple[List[Tuple[str, str]], dict, Set[Tuple[bpy.types.Image, Path]]]:
        """Extract the textures to transfer, copy them to the resource directory and remap the node paths.

        Args:
            instance (dict): Instance with textures
            images (set): Blender Images to publish

        Returns:
            Tuple[Tuple[str, str], dict, Set[Tuple[bpy.types.Image, Path]]]:
                (Files to copy and transfer with published blend,
                source hashes for later file optim,
                remapped images with source file path)
        """
        # Process the resource files
        transfers = []
        hashes = {}
        remapped = set()
        for image in images:
            # Check image is not internal
            if not image.filepath:
                continue

            # Get source and destination paths
            sourcepath = Path(bpy.path.abspath(image.filepath))
            destination = Path(instance.data["resourcesDir"], sourcepath.name)

            transfers.append((sourcepath.as_posix(), destination.as_posix()))
            self.log.info(f"file will be copied {sourcepath} -> {destination}")

            # Store the hashes from hash to destination to include in the
            # database
            # NOTE Keep source hash system in case HARDLINK system works again
            texture_hash = openpype.api.source_hash(sourcepath.as_posix())
            hashes[texture_hash] = destination.as_posix()

            # Remap source image to resources directory
            image.filepath = (
                f"//{destination.relative_to(instance.data['publishDir'])}"
            )

            # Keep remapped to restore after publishing
            remapped.add((image, sourcepath))

        self.log.info("Finished remapping destinations...")

        return transfers, hashes, remapped

    def _process_texture(self, filepath: Path, force: bool) -> Tuple[str, str]:
        """Process a single texture file on disk for publishing.
        This will:
            1. Check whether it's already published, if so it will do hardlink
            2. If not published and maketx is enabled, generate a new .tx file.
            3. Compute the destination path for the source file.
        Args:
            filepath (str): The source file path to process.
        Returns: TODO
        """
        # Hash source texture to match if already published
        texture_hash = openpype.api.source_hash(filepath.as_posix())

        # If source has been published before with the same settings,
        # then don't reprocess but hardlink from the original
        existing = legacy_io.distinct(
            f"data.sourceHashes.{texture_hash}", {"type": "version"}
        )
        if existing and not force:
            self.log.info("Found hash in database, preparing hardlink...")
            source = next((p for p in existing if os.path.exists(p)), None)
            if source:
                return "HARDLINK", texture_hash
            else:
                self.log.warning(
                    (
                        "Paths not found on disk, "
                        f"skipping hardlink: {existing}"
                    )
                )

        return "COPY", texture_hash

    def _resource_destination(self, instance: dict, filepath: Path) -> Path:
        """Get resource destination path.

        Args:
            instance (dict): Current Instance.
            filepath (Path): Resource path

        Returns:
            Path: Path to resource file
        """
        resources_dir = instance.data["resourcesDir"]

        return Path(resources_dir, filepath.name)
