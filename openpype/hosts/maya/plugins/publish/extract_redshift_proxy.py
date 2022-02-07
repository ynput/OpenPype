# -*- coding: utf-8 -*-
"""Redshift Proxy extractor."""
import os

from maya import cmds

import openpype.api
from openpype.hosts.maya.api.lib import maintained_selection


class ExtractRedshiftProxy(openpype.api.Extractor):
    """Extract the content of the instance to a redshift proxy file."""

    label = "Redshift Proxy (.rs)"
    hosts = ["maya"]
    families = ["redshiftproxy"]

    def process(self, instance):
        """Extractor entry point."""

        staging_dir = self.staging_dir(instance)
        file_name = "{}.rs".format(instance.name)
        file_path = os.path.join(staging_dir, file_name)

        anim_on = instance.data["animation"]
        rs_options = "exportConnectivity=0;enableCompression=1;keepUnused=0;"
        repr_files = file_name

        if not anim_on:
            # Remove animation information because it is not required for
            # non-animated subsets
            instance.data.pop("proxyFrameStart", None)
            instance.data.pop("proxyFrameEnd", None)

        else:
            start_frame = instance.data["proxyFrameStart"]
            end_frame = instance.data["proxyFrameEnd"]
            rs_options = "{}startFrame={};endFrame={};frameStep={};".format(
                rs_options, start_frame,
                end_frame, instance.data["proxyFrameStep"]
            )

            root, ext = os.path.splitext(file_path)
            # Padding is taken from number of digits of the end_frame.
            # Not sure where Redshift is taking it.
            repr_files = [
                "{}.{}{}".format(root, str(frame).rjust(4, "0"), ext)  # noqa: E501
                for frame in range(
                    int(start_frame),
                    int(end_frame) + 1,
                    int(instance.data["proxyFrameStep"]),
            )]
        # vertex_colors = instance.data.get("vertexColors", False)

        # Write out rs file
        self.log.info("Writing: '%s'" % file_path)
        with maintained_selection():
            cmds.select(instance.data["setMembers"], noExpand=True)
            cmds.file(file_path,
                      pr=False,
                      force=True,
                      type="Redshift Proxy",
                      exportSelected=True,
                      options=rs_options)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        self.log.debug("Files: {}".format(repr_files))

        representation = {
            'name': 'rs',
            'ext': 'rs',
            'files': repr_files,
            "stagingDir": staging_dir,
        }
        if anim_on:
            representation["frameStart"] = instance.data["proxyFrameStart"]
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '%s' to: %s"
                      % (instance.name, staging_dir))
