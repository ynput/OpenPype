# -*- coding: utf-8 -*-
"""Maya look extractor."""
import logging
from abc import ABCMeta, abstractmethod

import six
import os
import json
import tempfile
import platform
import contextlib
from collections import OrderedDict
import attr

from maya import cmds  # noqa

import pyblish.api

from openpype.lib.vendor_bin_utils import find_executable
from openpype.lib import source_hash, run_subprocess
from openpype.pipeline import legacy_io, publish, KnownPublishError
from openpype.hosts.maya.api import lib
from openpype.hosts.maya.api.lib import image_info, guess_colorspace

# Modes for transfer
COPY = 1
HARDLINK = 2


@attr.s
class TextureResult:
    # Path to the file
    path = attr.ib()
    # Colorspace of the resulting texture. This might not be the input
    # colorspace of the texture if a TextureProcessor has processed the file.
    colorspace = attr.ib()
    # Hash generated for the texture using openpype.lib.source_hash
    file_hash = attr.ib()
    # The transfer mode, e.g. COPY or HARDLINK
    transfer_mode = attr.ib()


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


@six.add_metaclass(ABCMeta)
class TextureProcessor:
    def __init__(self, log=None):
        if log is None:
            log = logging.getLogger(self.__class__.__name__)
        self.log = log

    def apply_settings(self, system_settings, project_settings):
        pass

    @abstractmethod
    def process(self,
                source,
                colorspace,
                color_management,
                staging_dir):
        """Process the `source` texture.

        Must be implemented on inherited class.

        This must always return a TextureResult even when it does not generate
        a texture. If it doesn't generate a texture then it should return a
        TextureResult using the input path and colorspace.

        Args:
            source (str): Path to source file.
            colorspace (str): Colorspace of the source file.
            color_management (dict): Maya Color management data from
                `lib.get_color_management_preferences`
            staging_dir (str): Output directory to write to.

        Returns:
            TextureResult: The resulting texture information.

        """
        pass

    @staticmethod
    def get_extension():
        pass

    def __repr__(self):
        # Log instance as class name
        return self.__class__.__name__


class MakeRSTexBin(TextureProcessor):
    """Make `.rstexbin` using `redshiftTextureProcessor`"""

    def process(self,
                source,
                colorspace,
                color_management,
                staging_dir):
        """
        with some default settings.

        This function requires the `REDSHIFT_COREDATAPATH`
        to be in `PATH`.

        Args:
            source (str): Path to source file.

        """
        if "REDSHIFT_COREDATAPATH" not in os.environ:
            raise RuntimeError("Must have Redshift available.")

        texture_processor_path = self.get_redshift_tool(
            "redshiftTextureProcessor"
        )
        if not texture_processor_path:
            raise KnownPublishError("Must have Redshift available.")

        subprocess_args = [
            texture_processor_path,
            source
        ]

        hash_args = ["rstex"]
        texture_hash = source_hash(source, *hash_args)

        self.log.debug(" ".join(subprocess_args))
        try:
            out = run_subprocess(subprocess_args)
        except Exception:
            self.log.error("Texture .rstexbin conversion failed",
                           exc_info=True)
            raise

        return TextureResult(
            path=out,
            file_hash=texture_hash,
            colorspace=colorspace,
            transfer_mode=COPY
        )

    @staticmethod
    def get_extension():
        return ".rstexbin"

    @staticmethod
    def get_redshift_tool(tool_name):
        """Path to redshift texture processor.

        On Windows it adds .exe extension if missing from tool argument.

        Args:
            tool (string): Tool name.

        Returns:
            str: Full path to redshift texture processor executable.
        """
        redshift_os_path = os.environ["REDSHIFT_COREDATAPATH"]

        redshift_tool_path = os.path.join(
            redshift_os_path,
            "bin",
            tool_name
        )

        return find_executable(redshift_tool_path)


class MakeTX(TextureProcessor):
    """Make `.tx` using `maketx` with some default settings.

    Some hardcoded arguments passed to `maketx` are based on the defaults used
    in Arnold's txManager tool.

    """

    def __init__(self, log=None):
        super(MakeTX, self).__init__(log=log)
        self.extra_args = []

    def apply_settings(self, system_settings, project_settings):
        # Allow extra maketx arguments from project settings
        extra_args_dict = (
            project_settings["maya"]["publish"]
            .get("ExtractLook", {}).get("maketx_arguments", {})
        )
        extra_args = []
        for flag, value in extra_args_dict.items():
            extra_args.append(flag)
            extra_args.append(value)
        self.extra_args = extra_args

    def process(self,
                source,
                colorspace,
                color_management,
                staging_dir):
        """Process the texture.

        This function requires the `maketx` executable to be
        available in the OIIO tool.

        Args:
            source (str): Path to source file.
            colorspace (str): Colorspace of the source file.
            color_management (dict): Maya Color management data from
                `lib.get_color_management_preferences`
            staging_dir (str): Output directory to write to.

        Returns:
            TextureResult: The resulting texture information.

        """
        from openpype.lib import get_oiio_tools_path

        maketx_path = get_oiio_tools_path("maketx")

        if not maketx_path:
            raise AssertionError(
                "OIIO 'maketx' tool not found. Result: {}".format(maketx_path)
            )

        # Define .tx filepath in staging if source file is not .tx
        fname, ext = os.path.splitext(os.path.basename(source))
        if ext == ".tx":
            # Do nothing if the source file is already a .tx file.
            return TextureResult(
                path=source,
                file_hash=None,     # todo: unknown texture hash?
                colorspace=colorspace,
                transfer_mode=COPY
            )

        args = []
        if color_management["enabled"]:
            config_path = color_management["config"]
            if not os.path.exists(config_path):
                raise RuntimeError("OCIO config not found at: "
                                   "{}".format(config_path))

            render_colorspace = color_management["rendering_space"]

            self.log.info("tx: converting colorspace {0} "
                          "-> {1}".format(colorspace,
                                          render_colorspace))
            args.extend(["--colorconvert", colorspace, render_colorspace])
            args.extend(["--colorconfig", config_path])

        else:
            # We can't rely on the colorspace attribute when not in color
            # managed mode because the collected color space is the color space
            # attribute of the file node which can be any string whatsoever
            # but only appears disabled in Attribute Editor. We assume we're
            # always converting to linear/Raw if the source file is assumed to
            # be sRGB.
            # TODO Without color management do we even know we can do
            #      "colorconvert" and what config does that end up using since
            #       colorconvert is a OCIO command line flag for maketx.
            #       Also, Raw != linear?
            render_colorspace = "linear"
            if self._has_arnold():
                img_info = image_info(source)
                color_space = guess_colorspace(img_info)
                if color_space.lower() == "sRGB":
                    self.log.info("tx: converting sRGB -> linear")
                    args.extend(["--colorconvert", "sRGB", "Raw"])
                else:
                    self.log.info("tx: texture's colorspace "
                                  "is already linear")
            else:
                self.log.warning("tx: cannot guess the colorspace, "
                                 "color conversion won't be "
                                 "available!")

        # Note: The texture hash is only reliable if we include any potential
        # conversion arguments provide to e.g. `maketx`
        hash_args = ["maketx"]
        hash_args.extend(args)
        hash_args.extend(self.extra_args)
        texture_hash = source_hash(source, *hash_args)

        # Exclude these additional arguments from the hashing because
        # it is the hash itself
        args.extend([
            "--sattrib",
            "sourceHash",
            texture_hash
        ])

        # Ensure folder exists
        destination = os.path.join(staging_dir, "resources", fname + ".tx")
        if not os.path.exists(os.path.dirname(destination)):
            os.makedirs(os.path.dirname(destination))

        self.log.info("Generating .tx file for %s .." % source)

        subprocess_args = [
            maketx_path,
            "-v",  # verbose
            "-u",  # update mode
            # unpremultiply before conversion (recommended when alpha present)
            "--unpremult",
            "--checknan",
            # use oiio-optimized settings for tile-size, planarconfig, metadata
            "--oiio",
            "--filter", "lanczos3",
            source
        ]

        subprocess_args.extend(args)
        if self.extra_args:
            subprocess_args.extend(self.extra_args)
        subprocess_args.extend(["-o", destination])

        self.log.debug(" ".join(subprocess_args))
        try:
            run_subprocess(subprocess_args)
        except Exception:
            self.log.error("Texture maketx conversion failed",
                           exc_info=True)
            raise

        return TextureResult(
            path=destination,
            file_hash=texture_hash,
            colorspace=render_colorspace,
            transfer_mode=COPY
        )

    @staticmethod
    def get_extension():
        return ".tx"

    @staticmethod
    def _has_arnold():
        """Return whether the arnold package is available and importable."""
        try:
            import arnold  # noqa: F401
            return True
        except (ImportError, ModuleNotFoundError):
            return False


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


class ExtractLook(publish.Extractor):
    """Extract Look (Maya Scene + JSON)

    Only extracts the sets (shadingEngines and alike) alongside a .json file
    that stores it relationships for the sets and "attribute" data for the
    instance members.

    """

    label = "Extract Look (Maya Scene + JSON)"
    hosts = ["maya"]
    families = ["look", "mvLook"]
    order = pyblish.api.ExtractorOrder + 0.2
    scene_type = "ma"
    look_data_type = "json"

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
        maya_path = os.path.join(dir_path, maya_fname)
        json_path = os.path.join(dir_path, json_fname)

        # Remove all members of the sets so they are not included in the
        # exported file by accident
        self.log.info("Processing sets..")
        lookdata = instance.data["lookData"]
        relationships = lookdata["relationships"]
        sets = list(relationships.keys())
        if not sets:
            self.log.info("No sets found")
            return

        # Specify texture processing executables to activate
        # TODO: Load these more dynamically once we support more processors
        processors = []
        context = instance.context
        for key, Processor in {
            # Instance data key to texture processor mapping
            "maketx": MakeTX,
            "rstex": MakeRSTexBin
        }.items():
            if instance.data.get(key, False):
                processor = Processor()
                processor.apply_settings(context.data["system_settings"],
                                         context.data["project_settings"])
                processors.append(processor)

        if processors:
            self.log.debug("Collected texture processors: "
                           "{}".format(processors))

        self.log.debug("Processing resources..")
        results = self.process_resources(instance,
                                         staging_dir=dir_path,
                                         processors=processors)
        transfers = results["fileTransfers"]
        hardlinks = results["fileHardlinks"]
        hashes = results["fileHashes"]
        remap = results["attrRemap"]

        # Extract in correct render layer
        self.log.info("Extracting look maya scene file: {}".format(maya_path))
        layer = instance.data.get("renderlayer", "defaultRenderLayer")
        with lib.renderlayer(layer):
            # TODO: Ensure membership edits don't become renderlayer overrides
            with lib.empty_sets(sets, force=True):
                # To avoid Maya trying to automatically remap the file
                # textures relative to the `workspace -directory` we force
                # it to a fake temporary workspace. This fixes textures
                # getting incorrectly remapped.
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

        self.log.info("Extracted instance '%s' to: %s" % (instance.name,
                                                          maya_path))

    def _set_resource_result_colorspace(self, resource, colorspace):
        """Update resource resulting colorspace after texture processing"""
        if "result_color_space" in resource:
            if resource["result_color_space"] == colorspace:
                return

            self.log.warning(
                "Resource already has a resulting colorspace but is now "
                "being overridden to a new one: {} -> {}".format(
                    resource["result_color_space"], colorspace
                )
            )
        resource["result_color_space"] = colorspace

    def process_resources(self, instance, staging_dir, processors):
        """Process all resources in the instance.

        It is assumed that all resources are nodes using file textures.

        Extract the textures to transfer, possibly convert with maketx and
        remap the node paths to the destination path. Note that a source
        might be included more than once amongst the resources as they could
        be the input file to multiple nodes.

        """

        resources = instance.data["resources"]
        color_management = lib.get_color_management_preferences()

        # Temporary fix to NOT create hardlinks on windows machines
        if platform.system().lower() == "windows":
            self.log.info(
                "Forcing copy instead of hardlink due to issues on Windows..."
            )
            force_copy = True
        else:
            force_copy = instance.data.get("forceCopy", False)

        # Process all resource's individual files
        processed_files = {}
        transfers = []
        hardlinks = []
        hashes = {}
        destinations = {}
        remap = OrderedDict()

        for resource in resources:
            colorspace = resource["color_space"]

            for filepath in resource["files"]:
                filepath = os.path.normpath(filepath)

                if filepath in processed_files:
                    # The file was already processed, likely due to usage by
                    # another resource in the scene. We confirm here it
                    # didn't do color spaces different than the current
                    # resource.
                    processed_file = processed_files[filepath]
                    self.log.debug(
                        "File was already processed. Likely used by another "
                        "resource too: {}".format(filepath)
                    )

                    if colorspace != processed_file["color_space"]:
                        self.log.warning(
                            "File was already processed but using another"
                            "colorspace: {} <-> {}"
                            "".format(colorspace,
                                      processed_file["color_space"]))

                    self._set_resource_result_colorspace(
                        resource,
                        colorspace=processed_file["result_color_space"]
                    )
                    continue

                texture_result = self._process_texture(
                    filepath,
                    processors=processors,
                    staging_dir=staging_dir,
                    force_copy=force_copy,
                    color_management=color_management,
                    colorspace=colorspace
                )
                source = texture_result.path
                destination = self.resource_destination(instance,
                                                        texture_result.path,
                                                        processors)

                # Set the resulting color space on the resource
                self._set_resource_result_colorspace(
                    resource, colorspace=texture_result.colorspace
                )

                processed_files[filepath] = {
                    "color_space": colorspace,
                    "result_color_space": texture_result.colorspace,
                }

                if force_copy or texture_result.transfer_mode == COPY:
                    transfers.append((source, destination))
                    self.log.info('file will be copied {} -> {}'.format(
                        source, destination))
                elif texture_result.transfer_mode == HARDLINK:
                    hardlinks.append((source, destination))
                    self.log.info('file will be hardlinked {} -> {}'.format(
                        source, destination))

                # Store the hashes from hash to destination to include in the
                # database
                hashes[texture_result.file_hash] = destination

            source = os.path.normpath(resource["source"])
            if source not in destinations:
                # Cache destination as source resource might be included
                # multiple times
                destinations[source] = self.resource_destination(
                    instance, source, processors
                )

            # Set up remapping attributes for the node during the publish
            # The order of these can be important if one attribute directly
            # affects another, e.g. we set colorspace after filepath because
            # maya sometimes tries to guess the colorspace when changing
            # filepaths (which is avoidable, but we don't want to have those
            # attributes changed in the resulting publish)
            # Remap filepath to publish destination
            filepath_attr = resource["attribute"]
            remap[filepath_attr] = destinations[source]

            # Preserve color space values (force value after filepath change)
            # This will also trigger in the same order at end of context to
            # ensure after context it's still the original value.
            node = resource["node"]
            if cmds.attributeQuery("colorSpace", node=node, exists=True):
                color_space_attr = "{}.colorSpace".format(node)
                remap[color_space_attr] = resource["result_color_space"]

        self.log.info("Finished remapping destinations ...")

        return {
            "fileTransfers": transfers,
            "fileHardlinks": hardlinks,
            "fileHashes": hashes,
            "attrRemap": remap,
        }

    def resource_destination(self, instance, filepath, processors):
        """Get resource destination path.

        This is utility function to change path if resource file name is
        changed by some external tool like `maketx`.

        Args:
            instance: Current Instance.
            filepath (str): Resource path
            processor: Texture processors converting resource.

        Returns:
            str: Path to resource file

        """
        resources_dir = instance.data["resourcesDir"]

        # Compute destination location
        basename, ext = os.path.splitext(os.path.basename(filepath))

        # Get extension from the last processor
        for processor in reversed(processors):
            processor_ext = processor.get_extension()
            if processor_ext:
                self.log.debug("Processor {} defined extension: "
                               "{}".format(processor, ext))
                ext = processor_ext
            break

        return os.path.join(
            resources_dir, basename + ext
        )

    def _get_existing_hashed_texture(self, texture_hash):
        """Return the first found filepath from a texture hash"""

        # If source has been published before with the same settings,
        # then don't reprocess but hardlink from the original
        existing = find_paths_by_hash(texture_hash)
        if existing:
            source = next((p for p in existing if os.path.exists(p)), None)
            if source:
                return source
            else:
                self.log.warning(
                    "Paths not found on disk, "
                    "skipping hardlink: {}".format(existing)
                )

    def _process_texture(self,
                         filepath,
                         processors,
                         staging_dir,
                         force_copy,
                         color_management,
                         colorspace):
        """Process a single texture file on disk for publishing.
        This will:
            1. Check whether it's already published, if so it will do hardlink
            2. If not published and maketx is enabled, generate a new .tx file.
            3. Compute the destination path for the source file.

        Args:
            filepath (str): The source file path to process.
            processors (list): List of TextureProcessor processing the texture
            staging_dir (str): The staging directory to write to.
            force_copy (bool): Whether to force a copy even if a file hash
                might have existed already in the project, otherwise
                hardlinking the existing file is allowed.
            color_management (dict): Maya's Color Management settings from
                `lib.get_color_management_preferences`
            colorspace (str): The source colorspace of the resources this
                texture belongs to.

        Returns:
            TextureResult: The texture result information.
        """

        if len(processors) > 1:
            raise KnownPublishError(
                "More than one texture processor not supported. "
                "Current processors enabled: {}".format(processors)
            )

        for processor in processors:
            self.log.debug("Processing texture {} with processor {}".format(
                filepath, processor
            ))

            processed_result = processor.process(filepath,
                                                 colorspace,
                                                 color_management,
                                                 staging_dir)
            if not processed_result:
                raise RuntimeError("Texture Processor {} returned "
                                   "no result.".format(processor))
            self.log.info("Generated processed "
                          "texture: {}".format(processed_result.path))

            # TODO: Currently all processors force copy instead of allowing
            #       hardlinks using source hashes. This should be refactored
            return processed_result

        # No texture processing for this file
        texture_hash = source_hash(filepath)
        if not force_copy:
            existing = self._get_existing_hashed_texture(filepath)
            if existing:
                self.log.info("Found hash in database, preparing hardlink..")
                return TextureResult(
                    path=filepath,
                    file_hash=texture_hash,
                    colorspace=colorspace,
                    transfer_mode=HARDLINK
                )

        return TextureResult(
            path=filepath,
            file_hash=texture_hash,
            colorspace=colorspace,
            transfer_mode=COPY
        )


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
