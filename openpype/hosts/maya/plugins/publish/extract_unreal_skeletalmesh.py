# -*- coding: utf-8 -*-
"""Create Unreal Skeletal Mesh data to be extracted as FBX."""
import os

from maya import cmds  # noqa

import pyblish.api
import openpype.api
from openpype.hosts.maya.api.lib import (
    parent_nodes,
    maintained_selection
)
from openpype.hosts.maya.api import fbx


class ExtractUnrealSkeletalMesh(openpype.api.Extractor):
    """Extract Unreal Skeletal Mesh as FBX from Maya. """

    order = pyblish.api.ExtractorOrder - 0.1
    label = "Extract Unreal Skeletal Mesh"
    families = ["skeletalMesh"]

    def process(self, instance):
        fbx_exporter = fbx.FBXExtractor(log=self.log)

        # Define output path
        staging_dir = self.staging_dir(instance)
        filename = "{0}.fbx".format(instance.name)
        path = os.path.join(staging_dir, filename)

        geo = instance.data.get("geometry")
        joints = instance.data.get("joints")

        to_extract = geo + joints

        # The export requires forward slashes because we need
        # to format it into a string in a mel expression
        path = path.replace('\\', '/')

        self.log.info("Extracting FBX to: {0}".format(path))
        self.log.info("Members: {0}".format(to_extract))
        self.log.info("Instance: {0}".format(instance[:]))

        fbx_exporter.set_options_from_instance(instance)

        parent = "{}{}".format(
            instance.data["asset"],
            instance.data.get("variant", "")
        )
        with maintained_selection():
            with parent_nodes(to_extract, parent=parent):
                rooted = [
                    "{}|{}".format(parent, i.split("|")[-1])
                    for i in to_extract
                ]
                self.log.info("Un-parenting: {}".format(rooted, path))
                fbx_exporter.export(rooted, path)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'fbx',
            'ext': 'fbx',
            'files': filename,
            "stagingDir": staging_dir,
        }
        instance.data["representations"].append(representation)

        self.log.info("Extract FBX successful to: {0}".format(path))
