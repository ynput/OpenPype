"""Plugin exporting psd files.
"""
import os
import json
import tempfile

import pyblish.api
from openpype.hosts.tvpaint.api import lib


class ExtractPsd(pyblish.api.InstancePlugin):
    order = pyblish.api.ExtractorOrder + 0.02
    label = "Extract PSD"
    hosts = ["tvpaint"]
    families = ["renderPass"]

    enabled = False

    def process(self, instance):
        george_script_lines = []
        repres = instance.data.get("representations")
        if not repres:
            return

        new_psd_repres = []
        for repre in repres:
            if repre['name'] != 'png':
                continue

            self.log.info("Processing representation: {}".format(
                json.dumps(repre, sort_keys=True, indent=4)
            ))

            output_dir = instance.data.get("stagingDir")
            if not output_dir or not os.path.exists(output_dir):
                # Create temp folder if staging dir is not set
                output_dir = (
                    tempfile.mkdtemp(prefix="tvpaint_export_json_psd_")
                ).replace("\\", "/")

            new_filenames = []

            for filename in repre['files']:
                new_filename = os.path.splitext(filename)[0]
                dst_filepath = os.path.join(repre["stagingDir"], new_filename)
                new_filenames.append(new_filename + '.psd')

                # george command to export psd files for each image
                george_script_lines.append(
                    "tv_clipsavestructure \"{}\" \"PSD\" \"image\" {}".format(
                        dst_filepath,
                        int(new_filename) - 1
                    )
                )

            new_psd_repres.append(
                {
                    "name": "psd",
                    "ext": "psd",
                    "files": new_filenames,
                    "stagingDir": output_dir,
                    "tags": "psd"
                }
            )

        lib.execute_george_through_file("\n".join(george_script_lines))

        instance.data["representations"].extend(new_psd_repres)

        self.log.info(
            "Representations: {}".format(
                json.dumps(
                    instance.data["representations"], sort_keys=True, indent=4
                )
            )
        )
