import re
import os
import json
import subprocess

import pyblish.api


class PublishImageSequence(pyblish.api.Extractor):
    """Extract result of saver by starting a comp render

    This will run the local render of Fusion,
    """

    order = pyblish.api.ExtractorOrder
    label = "Publish Rendered Image Sequence(s)"
    hosts = ["fusion"]
    targets = ["renderlocal"]

    def process(self, instance):

        context = instance.context
        subset = instance.data["subset"]
        output_directory = instance.data["outputDir"]
        ext = instance.data["ext"]

        # Regex to match resulting renders
        regex = "^{subset}.*[0-9]+.{ext}+$".format(subset=re.escape(subset),
                                                   ext=re.escape(ext))

        metadata = {
            "regex": regex,
            "startFrame": context.data["startFrame"],
            "endFrame": context.data["endFrame"],
            "asset": instance.data["asset"],
            "subset": subset
        }

        # Write metadata
        # todo: create temp file or more unique name for json
        path = os.path.join(output_directory,
                            "{}_metadata.json".format(subset))

        # Create subprocess command string
        from colorbleed.scripts import publish_imagesequence

        module_path = publish_imagesequence.__file__
        if module_path.endswith(".pyc"):
            module_path = module_path[:-len(".pyc")] + ".py"

        cmd = '{0} --paths"{1}"'.format(module_path, path)
        with open(path, "w") as f:
            json.dump(metadata, f)

            env = os.environ.copy()
            env["IMAGESEQUENCE"] = path

            subprocess.Popen(cmd,
                             env=env,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

            # todo: ensure publish went without any issues
            valid = bool(context)
            if not valid:
                raise RuntimeError("Unable to publish image sequences")

