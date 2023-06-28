import os
import six

from maya import cmds
from maya import mel

import pyblish.api
from openpype.pipeline import publish
from openpype.hosts.maya.api.lib import maintained_selection


class ExtractMultiverseUsd(publish.Extractor):
    """Extractor for Multiverse USD Asset data.

    This will extract settings for a Multiverse Write Asset operation:
    they are visible in the Maya set node created by a Multiverse USD
    Asset instance creator.

    The input data contained in the set is:

    - a single hierarchy of Maya nodes. Multiverse supports a variety of Maya
      nodes such as transforms, mesh, curves, particles, instances, particle
      instancers, pfx, MASH, lights, cameras, joints, connected materials,
      shading networks etc. including many of their attributes.

    Upon publish a .usd (or .usdz) asset file will be typically written.
    """

    label = "Extract Multiverse USD Asset"
    hosts = ["maya"]
    families = ["usd"]
    scene_type = "usd"
    file_formats = ["usd", "usda", "usdz"]

    @property
    def options(self):
        """Overridable options for Multiverse USD Export

        Given in the following format
            - {NAME: EXPECTED TYPE}

        If the overridden option's type does not match,
        the option is not included and a warning is logged.

        """

        return {
            "stripNamespaces": bool,
            "mergeTransformAndShape": bool,
            "writeAncestors": bool,
            "flattenParentXforms": bool,
            "writeSparseOverrides": bool,
            "useMetaPrimPath": bool,
            "customRootPath": str,
            "customAttributes": str,
            "nodeTypesToIgnore": str,
            "writeMeshes": bool,
            "writeCurves": bool,
            "writeParticles": bool,
            "writeCameras": bool,
            "writeLights": bool,
            "writeJoints": bool,
            "writeCollections": bool,
            "writePositions": bool,
            "writeNormals": bool,
            "writeUVs": bool,
            "writeColorSets": bool,
            "writeTangents": bool,
            "writeRefPositions": bool,
            "writeBlendShapes": bool,
            "writeDisplayColor": bool,
            "writeSkinWeights": bool,
            "writeMaterialAssignment": bool,
            "writeHardwareShader": bool,
            "writeShadingNetworks": bool,
            "writeTransformMatrix": bool,
            "writeUsdAttributes": bool,
            "writeInstancesAsReferences": bool,
            "timeVaryingTopology": bool,
            "customMaterialNamespace": str,
            "numTimeSamples": int,
            "timeSamplesSpan": float
        }

    @property
    def default_options(self):
        """The default options for Multiverse USD extraction."""

        return {
            "stripNamespaces": False,
            "mergeTransformAndShape": False,
            "writeAncestors": False,
            "flattenParentXforms": False,
            "writeSparseOverrides": False,
            "useMetaPrimPath": False,
            "customRootPath": str(),
            "customAttributes": str(),
            "nodeTypesToIgnore": str(),
            "writeMeshes": True,
            "writeCurves": True,
            "writeParticles": True,
            "writeCameras": False,
            "writeLights": False,
            "writeJoints": False,
            "writeCollections": False,
            "writePositions": True,
            "writeNormals": True,
            "writeUVs": True,
            "writeColorSets": False,
            "writeTangents": False,
            "writeRefPositions": False,
            "writeBlendShapes": False,
            "writeDisplayColor": False,
            "writeSkinWeights": False,
            "writeMaterialAssignment": False,
            "writeHardwareShader": False,
            "writeShadingNetworks": False,
            "writeTransformMatrix": True,
            "writeUsdAttributes": False,
            "writeInstancesAsReferences": False,
            "timeVaryingTopology": False,
            "customMaterialNamespace": str(),
            "numTimeSamples": 1,
            "timeSamplesSpan": 0.0
        }

    def parse_overrides(self, instance, options):
        """Inspect data of instance to determine overridden options"""

        for key in instance.data:
            if key not in self.options:
                continue

            # Ensure the data is of correct type
            value = instance.data[key]
            if isinstance(value, six.text_type):
                value = str(value)
            if not isinstance(value, self.options[key]):
                self.log.warning(
                    "Overridden attribute {key} was of "
                    "the wrong type: {invalid_type} "
                    "- should have been {valid_type}".format(
                        key=key,
                        invalid_type=type(value).__name__,
                        valid_type=self.options[key].__name__))
                continue

            options[key] = value

        return options

    def get_default_options(self):
        self.log.info("ExtractMultiverseUsd get_default_options")
        return self.default_options

    def filter_members(self, members):
        return members

    def process(self, instance):

        # Load plugin first
        cmds.loadPlugin("MultiverseForMaya", quiet=True)

        # Define output file path
        staging_dir = self.staging_dir(instance)
        file_format = instance.data.get("fileFormat", 0)
        if file_format in range(len(self.file_formats)):
            self.scene_type = self.file_formats[file_format]
        file_name = "{0}.{1}".format(instance.name, self.scene_type)
        file_path = os.path.join(staging_dir, file_name)
        file_path = file_path.replace('\\', '/')

        # Parse export options
        options = self.get_default_options()
        options = self.parse_overrides(instance, options)
        self.log.info("Export options: {0}".format(options))

        # Perform extraction
        self.log.info("Performing extraction ...")

        with maintained_selection():
            members = instance.data("setMembers")
            self.log.info('Collected objects: {}'.format(members))
            members = self.filter_members(members)
            if not members:
                self.log.error('No members!')
                return
            self.log.info(' - filtered: {}'.format(members))

            import multiverse

            time_opts = None
            frame_start = instance.data['frameStart']
            frame_end = instance.data['frameEnd']
            if frame_end != frame_start:
                time_opts = multiverse.TimeOptions()

                time_opts.writeTimeRange = True

                handle_start = instance.data['handleStart']
                handle_end = instance.data['handleEnd']

                time_opts.frameRange = (
                    frame_start - handle_start, frame_end + handle_end)
                time_opts.frameIncrement = instance.data['step']
                time_opts.numTimeSamples = instance.data.get(
                    'numTimeSamples', options['numTimeSamples'])
                time_opts.timeSamplesSpan = instance.data.get(
                    'timeSamplesSpan', options['timeSamplesSpan'])
                time_opts.framePerSecond = instance.data.get(
                    'fps', mel.eval('currentTimeUnitToFPS()'))

            asset_write_opts = multiverse.AssetWriteOptions(time_opts)
            options_discard_keys = {
                'numTimeSamples',
                'timeSamplesSpan',
                'frameStart',
                'frameEnd',
                'handleStart',
                'handleEnd',
                'step',
                'fps'
            }
            self.log.debug("Write Options:")
            for key, value in options.items():
                if key in options_discard_keys:
                    continue

                self.log.debug(" - {}={}".format(key, value))
                setattr(asset_write_opts, key, value)

            self.log.info('WriteAsset: {} / {}'.format(file_path, members))
            multiverse.WriteAsset(file_path, members, asset_write_opts)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': self.scene_type,
            'ext': self.scene_type,
            'files': file_name,
            'stagingDir': staging_dir
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance {} to {}".format(
            instance.name, file_path))


class ExtractMultiverseUsdAnim(ExtractMultiverseUsd):
    """Extractor for Multiverse USD Animation Sparse Cache data.

    This will extract the sparse cache data from the scene and generate a
    USD file with all the animation data.

    Upon publish a .usd sparse cache will be written.
    """
    label = "Extract Multiverse USD Animation Sparse Cache"
    families = ["animation", "usd"]
    match = pyblish.api.Subset

    def get_default_options(self):
        anim_options = self.default_options
        anim_options["writeSparseOverrides"] = True
        anim_options["writeUsdAttributes"] = True
        anim_options["stripNamespaces"] = True
        return anim_options

    def filter_members(self, members):
        out_set = next((i for i in members if i.endswith("out_SET")), None)

        if out_set is None:
            self.log.warning("Expecting out_SET")
            return None

        members = cmds.ls(cmds.sets(out_set, query=True), long=True)
        return members
