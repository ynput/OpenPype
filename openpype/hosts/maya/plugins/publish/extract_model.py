# -*- coding: utf-8 -*-
"""Extract model as Maya Scene."""
import os

from maya import cmds

import openpype.api
from openpype.hosts.maya.api import lib


class ExtractModel(openpype.api.Extractor):
    """Extract as Model (Maya Scene).

    Only extracts contents based on the original "setMembers" data to ensure
    publishing the least amount of required shapes. From that it only takes
    the shapes that are not intermediateObjects

    During export it sets a temporary context to perform a clean extraction.
    The context ensures:
        - Smooth preview is turned off for the geometry
        - Default shader is assigned (no materials are exported)
        - Remove display layers

    """

    label = "Model (Maya Scene)"
    hosts = ["maya"]
    families = ["model"]
    scene_type = "ma"
    optional = True

    def process(self, instance):
        """Plugin entry point."""
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
        # Define extract output file path
        stagingdir = self.staging_dir(instance)
        filename = "{0}.{1}".format(instance.name, self.scene_type)
        path = os.path.join(stagingdir, filename)

        # Perform extraction
        self.log.info("Performing extraction ...")

        # Get only the shape contents we need in such a way that we avoid
        # taking along intermediateObjects
        members = instance.data("setMembers")
        members = cmds.ls(members,
                          dag=True,
                          shapes=True,
                          type=("mesh", "nurbsCurve"),
                          noIntermediate=True,
                          long=True)

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
                                  force=True,
                                  typ="mayaAscii" if self.scene_type == "ma" else "mayaBinary",  # noqa: E501
                                  exportSelected=True,
                                  preserveReferences=False,
                                  channels=False,
                                  constraints=False,
                                  expressions=False,
                                  constructionHistory=False)

                        # Store reference for integration

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': self.scene_type,
            'ext': self.scene_type,
            'files': filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '%s' to: %s" % (instance.name, path))
