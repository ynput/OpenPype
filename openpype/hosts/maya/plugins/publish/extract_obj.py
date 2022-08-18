# -*- coding: utf-8 -*-
import os

from maya import cmds
import maya.mel as mel
import pyblish.api
import openpype.api
from openpype.hosts.maya.api.lib import maintained_selection

from openpype.hosts.maya.api import obj


class ExtractObj(openpype.api.Extractor):
    """Extract OBJ from Maya.

    This extracts reproducible OBJ exports ignoring any of the settings
    set on the local machine in the OBJ export options window.

    """
    order = pyblish.api.ExtractorOrder
    label = "Extract OBJ"
    families = ["obj"]

    def process(self, instance):
        obj_exporter = obj.OBJExtractor(log=self.log)

        # Define output path

        staging_dir = self.staging_dir(instance)
        filename = "{0}.fbx".format(instance.name)
        path = os.path.join(staging_dir, filename)

        # The export requires forward slashes because we need to
        # format it into a string in a mel expression
        path = path.replace('\\', '/')

        self.log.info("Extracting OBJ to: {0}".format(path))

        members = instance.data["setMembners"]
        self.log.info("Members: {0}".format(members))
        self.log.info("Instance: {0}".format(instance[:]))

        obj_exporter.set_options_from_instance(instance)

        # Export
        with maintained_selection():
            obj_exporter.export(members, path)
            cmds.select(members, r=1, noExpand=True)
            mel.eval('file -force -options "{0};{1};{2};{3};{4}" -typ "OBJexport" -pr -es "{5}";'.format(grp_flag, ptgrp_flag, mats_flag, smooth_flag, normals_flag, path)) # noqa

        if "representation" not in instance.data:
            instance.data["representation"] = []

        representation = {
            'name':'obj',
            'ext':'obx',
            'files': filename,
            "stagingDir": staging_dir,
        }
        instance.data["representations"].append(representation)

        self.log.info("Extract OBJ successful to: {0}".format(path))
