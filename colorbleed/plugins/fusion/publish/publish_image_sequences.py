import re
import os
import json
import subprocess

import pyblish.api


def _get_script():
    """Get path to the image sequence script"""

    # todo: use a more elegant way to get the python script

    try:
        from colorbleed.scripts import publish_filesequence
    except Exception:
        raise RuntimeError("Expected module 'publish_imagesequence'"
                           "to be available")

    module_path = publish_filesequence.__file__
    if module_path.endswith(".pyc"):
        module_path = module_path[:-len(".pyc")] + ".py"

    return module_path


class PublishImageSequence(pyblish.api.Extractor):
    """Publish the generated local image sequences."""

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Publish Rendered Image Sequence(s)"
    hosts = ["fusion"]
    targets = ["renderlocal"]
    families = ["fusion.local"]

    def process(self, instance):

        subset = instance.data["subset"]
        ext = instance.data["ext"]

        # Regex to match resulting renders
        regex = "^{subset}.*[0-9]+.{ext}+$".format(subset=re.escape(subset),
                                                   ext=re.escape(ext))

        # The instance has most of the information already stored
        metadata = {
            "regex": regex,
            "startFrame": instance.context.data["startFrame"],
            "endFrame": instance.context.data["endFrame"],
            "families": ["colorbleed.imagesequence"],
        }

        # Write metadata and store the path in the instance
        output_directory = instance.data["outputDir"]
        path = os.path.join(output_directory,
                            "{}_metadata.json".format(subset))
        with open(path, "w") as f:
            json.dump(metadata, f)

        assert os.path.isfile(path), ("Stored path is not a file for %s"
                                      % instance.data["name"])

        # Suppress any subprocess console
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        process = subprocess.Popen(["python", _get_script(),
                                    "--paths", path],
                                   bufsize=1,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   startupinfo=startupinfo)

        while True:
            output = process.stdout.readline()
            # Break when there is no output or a return code has been given
            if output == '' and process.poll() is not None:
                process.stdout.close()
                break
            if output:
                line = output.strip()
                if line.startswith("ERROR"):
                    self.log.error(line)
                else:
                    self.log.info(line)

        if process.returncode != 0:
            raise RuntimeError("Process quit with non-zero "
                               "return code: {}".format(process.returncode))
