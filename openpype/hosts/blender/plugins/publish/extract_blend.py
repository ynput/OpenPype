import os
from pathlib import Path
from typing import List, Set, Tuple

import bpy
import openpype.api

from openpype.pipeline import (
    legacy_io,
    publish,
)
from openpype.hosts.blender.api import plugin, get_compress_setting
from openpype.settings.lib import get_project_settings


class ExtractBlend(publish.Extractor):
    """Extract the scene as blend file."""

    label = "Extract Blend"
    hosts = ["blender"]
    families = ["model", "camera", "rig", "layout", "setdress"]
    optional = True

    pack_images = True  # TODO must be a OP setting

    def process(self, instance):
        # Define extract output file path
        stagingdir = self.staging_dir(instance)
        filename = f"{instance.name}.blend"
        filepath = Path(stagingdir, filename)

        # If paths management, make paths absolute before saving
        project_name = instance.data["projectEntity"]["name"]
        project_settings = get_project_settings(project_name)
        host_name = instance.context.data["hostName"]
        host_settings = project_settings.get(host_name)
        if host_settings.get("general", {}).get("use_paths_management"):
            bpy.ops.file.make_paths_absolute()

        # Perform extraction
        self.log.info("Performing extraction..")

        # Make camera visible in viewport
        camera = bpy.context.scene.camera
        is_camera_hidden_viewport = camera.hide_viewport
        camera.hide_viewport = False

        # Set object mode
        with plugin.context_override(
            active=bpy.context.scene.objects[0],
            selected=bpy.context.scene.objects,
        ):
            bpy.ops.object.mode_set()

        # Set camera hide in viewport back to its original value
        if is_camera_hidden_viewport:
            camera.hide_viewport = True

        plugin.deselect_all()

        data_blocks = set(instance)

        # Substitute objects by their collections to avoid data duplication
        collections = set(plugin.get_collections_by_objects(data_blocks))
        if collections:
            data_blocks.update(collections)

        # Get images used by datablocks and process resources
        used_images = self._get_used_images(data_blocks)
        transfers, hashes, remapped = self._process_resources(
            instance, used_images
        )

        # Pack used images in the blend files.
        packed_images = set()
        # TODO setting
        # if self.pack_images:
        #     for image in used_images:
        #         if not image.packed_file and image.source != "GENERATED":
        #             packed_images.add((image, image.is_dirty))
        #             image.pack()

        self._write_data(filepath, data_blocks)

        # restor packed images.
        for image, is_dirty in packed_images:
            if not image.filepath:
                unpack_method = "REMOVE"
            elif is_dirty:
                unpack_method = "WRITE_ORIGINAL"
            else:
                unpack_method = "USE_ORIGINAL"
            image.unpack(method=unpack_method)

        plugin.deselect_all()

        # Create representation dict
        representation = {
            "name": "blend",
            "ext": "blend",
            "files": filename,
            "stagingDir": stagingdir,
        }
        instance.data.setdefault("representations", [])
        instance.data["representations"].append(representation)

        self.log.info(
            f"Extracted instance '{instance.name}' to: {representation}"
        )

        # Restore remapped path
        for image, sourcepath in remapped:
            image.filepath = str(sourcepath)

        # Set up the resources transfers/links for the integrator
        instance.data.setdefault("transfers", [])
        instance.data["transfers"].extend(transfers)

        # Source hash for the textures
        instance.data.setdefault("sourceHashes", [])
        instance.data["sourceHashes"] = hashes

    def _write_data(self, filepath: Path, datablocks: Set[bpy.types.ID]):
        """Write data to filepath.

        Args:
            filepath (Path): Filepath to write data to.
            datablocks (Set[bpy.types.ID]): Datablocks to write.
        """
        bpy.data.libraries.write(
            filepath.as_posix(),
            datablocks,
            fake_user=True,
            compress=get_compress_setting(),
        )

    def _get_used_images(
        self, datablocks: Set[bpy.types.ID] = None
    ) -> Set[bpy.types.Image]:
        """Get images used by the datablocks.

        Args:
            datablocks (Set[bpy.types.ID], optional): Datablocks to get images from. Defaults to None.

        Returns:
            Set[bpy.types.Image]: Images used.
        """
        return {
            img
            for img, users in bpy.data.user_map(subset=bpy.data.images).items()
            if users & datablocks
        }

    def _process_resources(
        self, instance: dict, images: set
    ) -> Tuple[List[Tuple[str, str]], dict, Set[Tuple[bpy.types.Image, Path]]]:
        """Extract the textures to transfer, copy them to the resource
        directory and remap the node paths.

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
        for image in {
            img
            for img in images
            if img.source in {"FILE", "SEQUENCE", "MOVIE"}
            and not img.packed_file
        }:
            # Skip image from library or internal
            if image.library or not image.filepath:
                continue

            # Get source and destination paths
            sourcepath = image.filepath  # Don't every modify source_image
            destination = Path(
                instance.data["resourcesDir"], Path(sourcepath).name
            )

            transfers.append((sourcepath, destination.as_posix()))
            self.log.info(f"file will be copied {sourcepath} -> {destination}")

            # Store the hashes from hash to destination to include in the
            # database
            # NOTE Keep source hash system in case HARDLINK system works again
            texture_hash = openpype.api.source_hash(sourcepath)
            hashes[texture_hash] = destination.as_posix()

            # Remap source image to resources directory
            image.filepath = bpy.path.relpath(
                destination.as_posix(), start=instance.data["publishDir"]
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
        Returns: Reference type, Texture hash
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
