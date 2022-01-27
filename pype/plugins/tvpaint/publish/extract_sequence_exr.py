import os
import json

import pyblish.api
import pype.api


class ExtractSequenceEXR(pyblish.api.InstancePlugin):

    # Offset to get after ExtractSequence plugin.
    order = pyblish.api.ExtractorOrder + 0.1
    label = "Extract Sequence EXR"
    hosts = ["tvpaint"]
    families = ["review", "renderPass", "renderLayer"]
    active = False

    def process(self, instance):
        ignore_names = ["thumbnail"]
        ignore_extensions = ["mp4"]
        old_representations = instance.data["representations"]
        new_representations = []
        for _, representation in enumerate(old_representations):
            if representation["name"] in ignore_names:
                continue

            if representation["ext"] in ignore_extensions:
                continue

            self.log.info(
                "Processing representation: {}".format(
                    json.dumps(representation, sort_keys=True, indent=4)
                )
            )

            files = []
            oiio_path = os.environ.get("PYPE_OIIO_PATH", "oiiotool")
            for f in representation["files"]:
                f = os.path.join(representation["stagingDir"], f)
                path, ext = os.path.splitext(f)
                output_path = path + ".exr"
                args = [
                    oiio_path, f,
                    "--compression", "DWAA",
                    "--colorconvert", "sRGB", "linear",
                    "-o", output_path
                ]
                pype.api.subprocess(args)
                files.append(output_path)

            new_representations.append(
                {
                    "name": "exr",
                    "ext": "exr",
                    "files": files,
                    "stagingDir": representation["stagingDir"],
                    "tags": representation["tags"]
                }
            )

            instance.data["representations"].remove(representation)

        instance.data["representations"].extend(new_representations)
        self.log.info(
            "Representations: {}".format(
                json.dumps(
                    instance.data["representations"], sort_keys=True, indent=4
                )
            )
        )
