# -*- coding: utf-8 -*-
"""Extract vrayscene from specified families."""
import os

import avalon.maya
import pype.api

from maya import cmds


class ExtractVrayscene(pype.api.Extractor):
    """Extractor for vrscene."""

    label = "VRay Scene (.vrscene)"
    hosts = ["maya"]
    families = ["vrayscene"]

    def process(self, instance):
        """Plugin entry point."""
        if instance.data.get("exportOnFarm"):
            self.log.info("vrayscenes will be exported on farm.")
            return

        staging_dir = self.staging_dir(instance)
        file_name = "{}.vrmesh".format(instance.name)
        file_path = os.path.join(staging_dir, file_name)

        # Write out vrscene file
        self.log.info("Writing: '%s'" % file_path)
        with avalon.maya.maintained_selection():
            cmds.select(instance.data["setMembers"], noExpand=True)
            cmds.file(file_path, type="V-Ray Scene", pr=True, ea=True)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'vrscene',
            'ext': 'vrscene',
            'files': file_name,
            "stagingDir": staging_dir,
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '%s' to: %s"
                      % (instance.name, staging_dir))
