# -*- coding: utf-8 -*-
import os

from maya import cmds  # noqa
import maya.mel as mel  # noqa
import pyblish.api
import openpype.api
from openpype.hosts.maya.api.lib import maintained_selection

from openpype.hosts.maya.api import fbx


class ExtractFBX(openpype.api.Extractor):
    """Extract FBX from Maya.

    This extracts reproducible FBX exports ignoring any of the
    settings set on the local machine in the FBX export options window.

    """
    order = pyblish.api.ExtractorOrder
    label = "Extract FBX"
    families = ["fbx"]

    def process(self, instance):
        fbx_exporter = fbx.FBXExtractor(log=self.log)

        # Define output path
        staging_dir = self.staging_dir(instance)
        filename = "{0}.fbx".format(instance.name)
        path = os.path.join(staging_dir, filename)

        # The export requires forward slashes because we need
        # to format it into a string in a mel expression
        path = path.replace('\\', '/')

        self.log.info("Extracting FBX to: {0}".format(path))

        members = instance.data["setMembers"]
        self.log.info("Members: {0}".format(members))
        self.log.info("Instance: {0}".format(instance[:]))

        fbx_exporter.set_options_from_instance(instance)

        # Export
        with maintained_selection():
            fbx_exporter.export(members, path)
            cmds.select(members, r=1, noExpand=True)
            mel.eval('FBXExport -f "{}" -s'.format(path))

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
