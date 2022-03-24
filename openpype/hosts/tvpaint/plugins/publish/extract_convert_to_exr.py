"""Plugin converting png files from ExtractSequence into exrs.

Requires:
    ExtractSequence - source of PNG
    ExtractReview - review was already created so we can convert to any exr
"""
import os
import json

import pyblish.api
from openpype.lib import (
    get_oiio_tools_path,
    run_subprocess,
)
from openpype.pipeline import KnownPublishError


class ExtractConvertToEXR(pyblish.api.InstancePlugin):
    # Offset to get after ExtractSequence plugin.
    order = pyblish.api.ExtractorOrder + 0.1
    label = "Extract Sequence EXR"
    hosts = ["tvpaint"]
    families = ["render"]

    enabled = False

    # Replace source PNG files or just add
    replace_pngs = True
    # EXR compression
    exr_compression = "ZIP"

    def process(self, instance):
        repres = instance.data.get("representations")
        if not repres:
            return

        oiio_path = get_oiio_tools_path()
        # Raise an exception when oiiotool is not available
        # - this can currently happen on MacOS machines
        if not os.path.exists(oiio_path):
            KnownPublishError(
                "OpenImageIO tool is not available on this machine."
            )

        new_repres = []
        for repre in repres:
            if repre["name"] != "png":
                continue

            self.log.info(
                "Processing representation: {}".format(
                    json.dumps(repre, sort_keys=True, indent=4)
                )
            )

            src_filepaths = set()
            new_filenames = []
            for src_filename in repre["files"]:
                dst_filename = os.path.splitext(src_filename)[0] + ".exr"
                new_filenames.append(dst_filename)

                src_filepath = os.path.join(repre["stagingDir"], src_filename)
                dst_filepath = os.path.join(repre["stagingDir"], dst_filename)

                src_filepaths.add(src_filepath)

                args = [
                    oiio_path, src_filepath,
                    "--compression", self.exr_compression,
                    # TODO how to define color conversion?
                    "--colorconvert", "sRGB", "linear",
                    "-o", dst_filepath
                ]
                run_subprocess(args)

            new_repres.append(
                {
                    "name": "exr",
                    "ext": "exr",
                    "files": new_filenames,
                    "stagingDir": repre["stagingDir"],
                    "tags": list(repre["tags"])
                }
            )

            if self.replace_pngs:
                instance.data["representations"].remove(repre)
                for filepath in src_filepaths:
                    os.remove(filepath)

        instance.data["representations"].extend(new_repres)
        self.log.info(
            "Representations: {}".format(
                json.dumps(
                    instance.data["representations"], sort_keys=True, indent=4
                )
            )
        )
