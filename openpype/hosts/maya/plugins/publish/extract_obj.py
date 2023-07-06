# -*- coding: utf-8 -*-
import os

from maya import cmds
import pyblish.api
from openpype.pipeline import publish
from openpype.hosts.maya.api import lib


class ExtractObj(publish.Extractor):
    """Extract OBJ from Maya.

    This extracts reproducible OBJ exports ignoring any of the settings
    set on the local machine in the OBJ export options window.

    """
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract OBJ"
    families = ["model"]

    def process(self, instance):

        # Define output path

        staging_dir = self.staging_dir(instance)
        filename = "{0}.obj".format(instance.name)
        path = os.path.join(staging_dir, filename)

        # The export requires forward slashes because we need to
        # format it into a string in a mel expression

        self.log.info("Extracting OBJ to: {0}".format(path))

        members = instance.data("setMembers")
        members = cmds.ls(members,
                          dag=True,
                          shapes=True,
                          type=("mesh", "nurbsCurve"),
                          noIntermediate=True,
                          long=True)
        self.log.info("Members: {0}".format(members))
        self.log.info("Instance: {0}".format(instance[:]))

        if not cmds.pluginInfo('objExport', query=True, loaded=True):
            cmds.loadPlugin('objExport')

        # Export
        with lib.no_display_layers(instance):
            with lib.displaySmoothness(members,
                                       divisionsU=0,
                                       divisionsV=0,
                                       pointsWire=4,
                                       pointsShaded=1,
                                       polygonObject=1):
                with lib.shader(members,
                                shadingEngine="initialShadingGroup"):
                    with lib.maintained_selection():
                        cmds.select(members, noExpand=True)
                        cmds.file(path,
                                  exportSelected=True,
                                  type='OBJexport',
                                  preserveReferences=True,
                                  force=True)

        if "representation" not in instance.data:
            instance.data["representation"] = []

        representation = {
            'name': 'obj',
            'ext': 'obj',
            'files': filename,
            "stagingDir": staging_dir,
        }
        instance.data["representations"].append(representation)

        self.log.info("Extract OBJ successful to: {0}".format(path))
