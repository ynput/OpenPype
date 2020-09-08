# -*- coding: utf-8 -*-
"""Convert exrs in representation to tiled exrs usin oiio tools."""
import os
import copy

import pyblish.api
import pype.api
import pype.lib


class ExtractScanlineExr(pyblish.api.InstancePlugin):
    """Convert tiled EXRs to scanline using OIIO tool."""

    label = "Extract Scanline EXR"
    hosts = ["shell"]
    order = pyblish.api.ExtractorOrder
    families = ["imagesequence", "render", "render2d", "source"]

    def process(self, instance):
        """Plugin entry point."""
        # get representation and loop them
        representations = instance.data["representations"]

        representations_new = []

        for repre in representations:
            self.log.info(
                "Processnig representation {}".format(repre.get("name")))
            tags = repre.get("tags", [])
            if "toScanline" not in tags:
                continue

            # run only on exrs
            if repre.get("ext") != "exr":
                continue

            if not isinstance(repre['files'], (list, tuple)):
                input_files = [repre['files']]
                self.log.info("We have a sequence.")
            else:
                input_files = repre['files']
                self.log.info("We have a single frame")

            stagingdir = os.path.normpath(repre.get("stagingDir"))

            oiio_tool_path = os.getenv("PYPE_OIIO_PATH", "")

            new_files = []
            for file in input_files:

                oiio_cmd = []
                oiio_cmd.append(oiio_tool_path)
                oiio_cmd.append(
                    os.path.join(stagingdir, file)
                )
                oiio_cmd.append("--scanline")
                oiio_cmd.append("-o")
                new_file = f"_scanline_{file}"
                new_files.append(new_file)
                oiio_cmd.append(os.path.join(stagingdir, new_file))

                subprocess_exr = " ".join(oiio_cmd)
                self.log.info(f"running: {subprocess_exr}")
                pype.api.subprocess(subprocess_exr)

                # raise error if there is no ouptput
                if not os.path.exists(os.path.join(stagingdir, new_file)):
                    self.log.error(
                        f"File {new_file} was not produced by oiio tool!")
                    raise AssertionError("OIIO tool conversion failed")

            if "representations" not in instance.data:
                instance.data["representations"] = []

            representation = copy.deepcopy(repre)

            representation['name'] = 'scanline_exr'
            representation['files'] = new_files if len(new_files) > 1 else new_files[0]  # noqa: E501
            representation['tags'] = []

            self.log.debug("Adding: {}".format(representation))
            representations_new.append(representation)

        instance.data["representations"] += representations_new
