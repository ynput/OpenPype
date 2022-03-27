# -*- coding: utf-8 -*-
"""Create Unreal Skeletal Mesh data to be extracted as FBX."""
import os
from contextlib import contextmanager

from maya import cmds  # noqa

import pyblish.api
import openpype.api
from openpype.hosts.maya.api.lib import (
    parent_nodes,
    maintained_selection
)
from openpype.hosts.maya.api import fbx


@contextmanager
def renamed(original_name, renamed_name):
    # type: (str, str) -> None
    try:
        cmds.rename(original_name, renamed_name)
        yield
    finally:
        cmds.rename(renamed_name, original_name)


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

        joints_parent = cmds.listRelatives(joints, p=True)

        to_extract = geo + joints

        # The export requires forward slashes because we need
        # to format it into a string in a mel expression
        path = path.replace('\\', '/')

        self.log.info("Extracting FBX to: {0}".format(path))
        self.log.info("Members: {0}".format(to_extract))
        self.log.info("Instance: {0}".format(instance[:]))

        fbx_exporter.set_options_from_instance(instance)

        # This magic is done for variants. To let Unreal merge correctly
        # existing data, top node must have the same name. So for every
        # variant we extract we need to rename top node of the rig correctly.
        # It is finally done in context manager so it won't affect current
        # scene.
        parent = "{}{}".format(
            instance.data["asset"],
            instance.data.get("variant", "")
        )

        joints_parents = cmds.ls(joints, long=True)
        geo_parents = cmds.ls(geo, long=True)

        parent_node = {
            parent.split("|")[1] for parent in (joints_parents + geo_parents)
        }.pop()

        renamed_to_extract = []
        for node in to_extract:
            node_path = node.split("|")
            node_path[1] = parent
            renamed_to_extract.append("|".join(node_path))

        with renamed(parent_node, parent):
            self.log.info("Extracting: {}".format(renamed_to_extract, path))
            fbx_exporter.export(renamed_to_extract, path)

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
