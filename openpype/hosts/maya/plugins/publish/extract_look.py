# -*- coding: utf-8 -*-
"""Maya look extractor."""
import os
import sys
import json
import tempfile
import platform
import contextlib
import subprocess
from collections import OrderedDict

from maya import cmds  # noqa

import pyblish.api

import openpype.api
from openpype.pipeline import legacy_io
from openpype.hosts.maya.api import lib

# Modes for transfer
COPY = 1
HARDLINK = 2


def escape_space(path):
    """Ensure path is enclosed by quotes to allow paths with spaces"""
    return '"{}"'.format(path) if " " in path else path


def find_paths_by_hash(texture_hash):
    """Find the texture hash key in the dictionary.

    All paths that originate from it.

    Args:
        texture_hash (str): Hash of the texture.

    Return:
        str: path to texture if found.

    """
    key = "data.sourceHashes.{0}".format(texture_hash)
    return legacy_io.distinct(key, {"type": "version"})


def maketx(source, destination, *args):
    """Make `.tx` using `maketx` with some default settings.

    The settings are based on default as used in Arnold's
    txManager in the scene.
    This function requires the `maketx` executable to be
    on the `PATH`.

    Args:
        source (str): Path to source file.
        destination (str): Writing destination path.
        *args: Additional arguments for `maketx`.

    Returns:
        str: Output of `maketx` command.

    """
    from openpype.lib import get_oiio_tools_path

    maketx_path = get_oiio_tools_path("maketx")

    if not os.path.exists(maketx_path):
        print(
            "OIIO tool not found in {}".format(maketx_path))
        raise AssertionError("OIIO tool not found")

    cmd = [
        maketx_path,
        "-v",  # verbose
        "-u",  # update mode
        # unpremultiply before conversion (recommended when alpha present)
        "--unpremult",
        "--checknan",
        # use oiio-optimized settings for tile-size, planarconfig, metadata
        "--oiio",
        "--filter lanczos3",
    ]

    cmd.extend(args)
    cmd.extend(["-o", escape_space(destination), escape_space(source)])

    cmd = " ".join(cmd)

    CREATE_NO_WINDOW = 0x08000000  # noqa
    kwargs = dict(args=cmd, stderr=subprocess.STDOUT)

    if sys.platform == "win32":
        kwargs["creationflags"] = CREATE_NO_WINDOW
    try:
        out = subprocess.check_output(**kwargs)
    except subprocess.CalledProcessError as exc:
        print(exc)
        import traceback

        traceback.print_exc()
        raise

    return out


@contextlib.contextmanager
def no_workspace_dir():
    """Force maya to a fake temporary workspace directory.

    Note: This is not maya.cmds.workspace 'rootDirectory' but the 'directory'

    This helps to avoid Maya automatically remapping image paths to files
    relative to the currently set directory.

    """

    # Store current workspace
    original = cmds.workspace(query=True, directory=True)

    # Set a fake workspace
    fake_workspace_dir = tempfile.mkdtemp()
    cmds.workspace(directory=fake_workspace_dir)

    try:
        yield
    finally:
        try:
            cmds.workspace(directory=original)
        except RuntimeError:
            # If the original workspace directory didn't exist either
            # ignore the fact that it fails to reset it to the old path
            pass

        # Remove the temporary directory
        os.rmdir(fake_workspace_dir)


class ExtractLook(openpype.api.Extractor):
    """Extract Look (Maya Scene + JSON)

    Only extracts the sets (shadingEngines and alike) alongside a .json file
    that stores it relationships for the sets and "attribute" data for the
    instance members.

    """

    label = "Extract Look (Maya Scene + JSON)"
    hosts = ["maya"]
    families = ["look"]
    order = pyblish.api.ExtractorOrder + 0.2
    scene_type = "ma"
    look_data_type = "json"

    @staticmethod
    def get_renderer_name():
        """Get renderer name from Maya.

        Returns:
            str: Renderer name.

        """
        renderer = cmds.getAttr(
            "defaultRenderGlobals.currentRenderer"
        ).lower()
        # handle various renderman names
        if renderer.startswith("renderman"):
            renderer = "renderman"
        return renderer

    def get_maya_scene_type(self, instance):
        """Get Maya scene type from settings.

        Args:
            instance (pyblish.api.Instance): Instance with collected
                project settings.

        """
        ext_mapping = (
            instance.context.data["project_settings"]["maya"]["ext_mapping"]
        )
        if ext_mapping:
            self.log.info("Looking in settings for scene type ...")
            # use extension mapping for first family found
            for family in self.families:
                try:
                    self.scene_type = ext_mapping[family]
                    self.log.info(
                        "Using {} as scene type".format(self.scene_type))
                    break
                except KeyError:
                    # no preset found
                    pass

        return "mayaAscii" if self.scene_type == "ma" else "mayaBinary"

    def process(self, instance):
        """Plugin entry point.

        Args:
            instance: Instance to process.

        """
        _scene_type = self.get_maya_scene_type(instance)

        # Define extract output file path
        dir_path = self.staging_dir(instance)
        maya_fname = "{0}.{1}".format(instance.name, self.scene_type)
        json_fname = "{0}.{1}".format(instance.name, self.look_data_type)

        # Make texture dump folder
        maya_path = os.path.join(dir_path, maya_fname)
        json_path = os.path.join(dir_path, json_fname)

        self.log.info("Performing extraction..")

        # Remove all members of the sets so they are not included in the
        # exported file by accident
        self.log.info("Extract sets (%s) ..." % _scene_type)
        lookdata = instance.data["lookData"]
        relationships = lookdata["relationships"]
        sets = list(relationships.keys())
        if not sets:
            self.log.info("No sets found")
            return

        results = self.process_resources(instance, staging_dir=dir_path)
        transfers = results["fileTransfers"]
        hardlinks = results["fileHardlinks"]
        hashes = results["fileHashes"]
        remap = results["attrRemap"]

        # Extract in correct render layer
        layer = instance.data.get("renderlayer", "defaultRenderLayer")
        with lib.renderlayer(layer):
            # TODO: Ensure membership edits don't become renderlayer overrides
            with lib.empty_sets(sets, force=True):
                # To avoid Maya trying to automatically remap the file
                # textures relative to the `workspace -directory` we force
                # it to a fake temporary workspace. This fixes textures
                # getting incorrectly remapped. (LKD-17, PLN-101)
                with no_workspace_dir():
                    with lib.attribute_values(remap):
                        with lib.maintained_selection():
                            cmds.select(sets, noExpand=True)
                            cmds.file(
                                maya_path,
                                force=True,
                                typ=_scene_type,
                                exportSelected=True,
                                preserveReferences=False,
                                channels=True,
                                constraints=True,
                                expressions=True,
                                constructionHistory=True,
                            )

        # Write the JSON data
        self.log.info("Extract json..")
        data = {
            "attributes": lookdata["attributes"],
            "relationships": relationships
        }

        with open(json_path, "w") as f:
            json.dump(data, f)

        if "files" not in instance.data:
            instance.data["files"] = []
        if "hardlinks" not in instance.data:
            instance.data["hardlinks"] = []
        if "transfers" not in instance.data:
            instance.data["transfers"] = []

        instance.data["files"].append(maya_fname)
        instance.data["files"].append(json_fname)

        if instance.data.get("representations") is None:
            instance.data["representations"] = []

        instance.data["representations"].append(
            {
                "name": self.scene_type,
                "ext": self.scene_type,
                "files": os.path.basename(maya_fname),
                "stagingDir": os.path.dirname(maya_fname),
            }
        )
        instance.data["representations"].append(
            {
                "name": self.look_data_type,
                "ext": self.look_data_type,
                "files": os.path.basename(json_fname),
                "stagingDir": os.path.dirname(json_fname),
            }
        )

        # Set up the resources transfers/links for the integrator
        instance.data["transfers"].extend(transfers)
        instance.data["hardlinks"].extend(hardlinks)

        # Source hash for the textures
        instance.data["sourceHashes"] = hashes

        """
        self.log.info("Returning colorspaces to their original values ...")
        for attr, value in remap.items():
            self.log.info("  - {}: {}".format(attr, value))
            cmds.setAttr(attr, value, type="string")
        """
        self.log.info("Extracted instance '%s' to: %s" % (instance.name,
                                                          maya_path))

    def process_resources(self, instance, staging_dir):

        # Extract the textures to transfer, possibly convert with maketx and
        # remap the node paths to the destination path. Note that a source
        # might be included more than once amongst the resources as they could
        # be the input file to multiple nodes.
        resources = instance.data["resources"]
        do_maketx = instance.data.get("maketx", False)

        # Collect all unique files used in the resources
        files_metadata = {}
        for resource in resources:
            # Preserve color space values (force value after filepath change)
            # This will also trigger in the same order at end of context to
            # ensure after context it's still the original value.
            color_space = resource.get("color_space")

            for f in resource["files"]:
                files_metadata[os.path.normpath(f)] = {
                    "color_space": color_space}

        # Process the resource files
        transfers = []
        hardlinks = []
        hashes = {}
        # Temporary fix to NOT create hardlinks on windows machines
        if platform.system().lower() == "windows":
            self.log.info(
                "Forcing copy instead of hardlink due to issues on Windows..."
            )
            force_copy = True
        else:
            force_copy = instance.data.get("forceCopy", False)

        for filepath in files_metadata:

            linearize = False
            if do_maketx and files_metadata[filepath]["color_space"].lower() == "srgb":  # noqa: E501
                linearize = True
                # set its file node to 'raw' as tx will be linearized
                files_metadata[filepath]["color_space"] = "Raw"

            # if do_maketx:
            #     color_space = "Raw"

            source, mode, texture_hash = self._process_texture(
                filepath,
                do_maketx,
                staging=staging_dir,
                linearize=linearize,
                force=force_copy
            )
            destination = self.resource_destination(instance,
                                                    source,
                                                    do_maketx)

            # Force copy is specified.
            if force_copy:
                mode = COPY

            if mode == COPY:
                transfers.append((source, destination))
                self.log.info('copying')
            elif mode == HARDLINK:
                hardlinks.append((source, destination))
                self.log.info('hardlinking')

            # Store the hashes from hash to destination to include in the
            # database
            hashes[texture_hash] = destination

        # Remap the resources to the destination path (change node attributes)
        destinations = {}
        remap = OrderedDict()  # needs to be ordered, see color space values
        for resource in resources:
            source = os.path.normpath(resource["source"])
            if source not in destinations:
                # Cache destination as source resource might be included
                # multiple times
                destinations[source] = self.resource_destination(
                    instance, source, do_maketx
                )

            # Preserve color space values (force value after filepath change)
            # This will also trigger in the same order at end of context to
            # ensure after context it's still the original value.
            color_space_attr = resource["node"] + ".colorSpace"
            try:
                color_space = cmds.getAttr(color_space_attr)
            except ValueError:
                # node doesn't have color space attribute
                color_space = "Raw"
            else:
                if files_metadata[source]["color_space"] == "Raw":
                    # set color space to raw if we linearized it
                    color_space = "Raw"
                # Remap file node filename to destination
                remap[color_space_attr] = color_space
            attr = resource["attribute"]
            remap[attr] = destinations[source]

        self.log.info("Finished remapping destinations ...")

        return {
            "fileTransfers": transfers,
            "fileHardlinks": hardlinks,
            "fileHashes": hashes,
            "attrRemap": remap,
        }

    def resource_destination(self, instance, filepath, do_maketx):
        """Get resource destination path.

        This is utility function to change path if resource file name is
        changed by some external tool like `maketx`.

        Args:
            instance: Current Instance.
            filepath (str): Resource path
            do_maketx (bool): Flag if resource is processed by `maketx`.

        Returns:
            str: Path to resource file

        """
        resources_dir = instance.data["resourcesDir"]

        # Compute destination location
        basename, ext = os.path.splitext(os.path.basename(filepath))

        # If `maketx` then the texture will always end with .tx
        if do_maketx:
            ext = ".tx"

        return os.path.join(
            resources_dir, basename + ext
        )

    def _process_texture(self, filepath, do_maketx, staging, linearize, force):
        """Process a single texture file on disk for publishing.
        This will:
            1. Check whether it's already published, if so it will do hardlink
            2. If not published and maketx is enabled, generate a new .tx file.
            3. Compute the destination path for the source file.
        Args:
            filepath (str): The source file path to process.
            do_maketx (bool): Whether to produce a .tx file
        Returns:
        """

        fname, ext = os.path.splitext(os.path.basename(filepath))

        args = []
        if do_maketx:
            args.append("maketx")
        texture_hash = openpype.api.source_hash(filepath, *args)

        # If source has been published before with the same settings,
        # then don't reprocess but hardlink from the original
        existing = find_paths_by_hash(texture_hash)
        if existing and not force:
            self.log.info("Found hash in database, preparing hardlink..")
            source = next((p for p in existing if os.path.exists(p)), None)
            if source:
                return source, HARDLINK, texture_hash
            else:
                self.log.warning(
                    ("Paths not found on disk, "
                     "skipping hardlink: %s") % (existing,)
                )

        if do_maketx and ext != ".tx":
            # Produce .tx file in staging if source file is not .tx
            converted = os.path.join(staging, "resources", fname + ".tx")

            if linearize:
                self.log.info("tx: converting sRGB -> linear")
                colorconvert = "--colorconvert sRGB linear"
            else:
                colorconvert = ""

            # Ensure folder exists
            if not os.path.exists(os.path.dirname(converted)):
                os.makedirs(os.path.dirname(converted))

            self.log.info("Generating .tx file for %s .." % filepath)
            maketx(
                filepath,
                converted,
                # Include `source-hash` as string metadata
                "-sattrib",
                "sourceHash",
                escape_space(texture_hash),
                colorconvert,
            )

            return converted, COPY, texture_hash

        return filepath, COPY, texture_hash


class ExtractModelRenderSets(ExtractLook):
    """Extract model render attribute sets as model metadata

    Only extracts the render attrib sets (NO shadingEngines) alongside
    a .json file that stores it relationships for the sets and "attribute"
    data for the instance members.

    """

    label = "Model Render Sets"
    hosts = ["maya"]
    families = ["model"]
    scene_type_prefix = "meta.render."
    look_data_type = "meta.render.json"

    def get_maya_scene_type(self, instance):
        typ = super(ExtractModelRenderSets, self).get_maya_scene_type(instance)
        # add prefix
        self.scene_type = self.scene_type_prefix + self.scene_type

        return typ
