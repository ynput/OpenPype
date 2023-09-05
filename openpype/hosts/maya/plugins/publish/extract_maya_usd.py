import os
import six

from maya import cmds

import pyblish.api
from openpype.pipeline import publish
from openpype.hosts.maya.api.lib import maintained_selection


class ExtractMayaUsd(publish.Extractor):
    """Extractor for Maya USD Asset data.

    Upon publish a .usd (or .usdz) asset file will typically be written.
    """

    label = "Extract Maya USD Asset"
    hosts = ["maya"]
    families = ["mayaUsd"]

    @property
    def options(self):
        """Overridable options for Maya USD Export

        Given in the following format
            - {NAME: EXPECTED TYPE}

        If the overridden option's type does not match,
        the option is not included and a warning is logged.

        """

        # TODO: Support more `mayaUSDExport` parameters
        return {
            "stripNamespaces": bool,
            "mergeTransformAndShape": bool,
            "exportDisplayColor": bool,
            "exportColorSets": bool,
            "exportInstances": bool,
            "exportUVs": bool,
            "exportVisibility": bool,
            "exportComponentTags": bool,
            "exportRefsAsInstanceable": bool,
            "eulerFilter": bool,
            "renderableOnly": bool,
            #"worldspace": bool,
        }

    @property
    def default_options(self):
        """The default options for Maya USD Export."""

        # TODO: Support more `mayaUSDExport` parameters
        return {
            "stripNamespaces": False,
            "mergeTransformAndShape": False,
            "exportDisplayColor": False,
            "exportColorSets": True,
            "exportInstances": True,
            "exportUVs": True,
            "exportVisibility": True,
            "exportComponentTags": True,
            "exportRefsAsInstanceable": False,
            "eulerFilter": True,
            "renderableOnly": False,
            #"worldspace": False
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

    def filter_members(self, members):
        # Can be overridden by inherited classes
        return members

    def process(self, instance):

        # Load plugin first
        cmds.loadPlugin("mayaUsdPlugin", quiet=True)

        # Define output file path
        staging_dir = self.staging_dir(instance)
        file_name = "{0}.usd".format(instance.name)
        file_path = os.path.join(staging_dir, file_name)
        file_path = file_path.replace('\\', '/')

        # Parse export options
        options = self.default_options
        options = self.parse_overrides(instance, options)
        self.log.info("Export options: {0}".format(options))

        # Perform extraction
        self.log.debug("Performing extraction ...")

        members = instance.data("setMembers")
        self.log.debug('Collected objects: {}'.format(members))
        members = self.filter_members(members)
        if not members:
            self.log.error('No members!')
            return

        start = instance.data["frameStartHandle"]
        end = instance.data["frameEndHandle"]

        with maintained_selection():
            self.log.debug('Exporting USD: {} / {}'.format(file_path, members))
            cmds.mayaUSDExport(file=file_path,
                               frameRange=(start, end),
                               frameStride=instance.data.get("step", 1.0),
                               exportRoots=members,
                               **options)

        representation = {
            'name': "usd",
            'ext': "usd",
            'files': file_name,
            'stagingDir': staging_dir
        }
        instance.data.setdefault("representations", []).append(representation)

        self.log.debug(
            "Extracted instance {} to {}".format(instance.name, file_path)
        )


class ExtractMayaUsdAnim(ExtractMayaUsd):
    """Extractor for Maya USD Animation Sparse Cache data.

    This will extract the sparse cache data from the scene and generate a
    USD file with all the animation data.

    Upon publish a .usd sparse cache will be written.
    """
    label = "Extract Maya USD Animation Sparse Cache"
    families = ["animation", "mayaUsd"]
    match = pyblish.api.Subset

    def filter_members(self, members):
        out_set = next((i for i in members if i.endswith("out_SET")), None)

        if out_set is None:
            self.log.warning("Expecting out_SET")
            return None

        members = cmds.ls(cmds.sets(out_set, query=True), long=True)
        return members
