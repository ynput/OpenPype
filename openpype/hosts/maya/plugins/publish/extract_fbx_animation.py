# -*- coding: utf-8 -*-
import os

from maya import cmds  # noqa
import pyblish.api

from openpype.pipeline import publish
from openpype.hosts.maya.api import fbx


class ExtractFBXAnimation(publish.Extractor):
    """Extract Rig in FBX format from Maya.

    This extracts the rig in fbx with the constraints
    and referenced asset content included.
    This also optionally extract animated rig in fbx with
    geometries included.

    """
    order = pyblish.api.ExtractorOrder
    label = "Extract Animation (FBX)"
    hosts = ["maya"]
    families = ["animation.fbx"]

    def process(self, instance):
        # Define output path
        staging_dir = self.staging_dir(instance)
        filename = "{0}.fbx".format(instance.name)
        path = os.path.join(staging_dir, filename)

        # The export requires forward slashes because we need
        # to format it into a string in a mel expression
        fbx_exporter = fbx.FBXExtractor(log=self.log)
        out_set = instance.data.get("animated_skeleton", [])
        # Export
        instance.data["constraints"] = True
        instance.data["skeletonDefinitions"] = True
        instance.data["referencedAssetsContent"] = True

        fbx_exporter.set_options_from_instance(instance)
        fbx_exporter.export(out_set, path.replace("\\", "/"))

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'fbx',
            'ext': 'fbx',
            'files': filename,
            "stagingDir": staging_dir
        }
        instance.data["representations"].append(representation)

        self.log.debug("Extract animated FBX successful to: {0}".format(path))
