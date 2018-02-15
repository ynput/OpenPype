import os
import subprocess

import pyblish.api


def _get_script():
    """Get path to the image sequence script"""

    # todo: use a more elegant way to get the python script

    try:
        from colorbleed.scripts import publish_filesequence
    except Exception as e:
        raise RuntimeError("Expected module 'publish_imagesequence'"
                           "to be available")

    module_path = publish_filesequence.__file__
    if module_path.endswith(".pyc"):
        module_path = module_path[:-len(".pyc")] + ".py"

    return module_path


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

        # Get metadata file, check if path is to an existing file
        path = instance.data.get("jsonpath", "")
        assert os.path.isfile(path), ("Stored path is not a file for %s"
                                      % instance.data["name"])

        # Get the script to execute
        script = _get_script()
        cmd = 'python {0} --paths "{1}"'.format(script, path)

        # Suppress any subprocess console
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        process = subprocess.Popen(cmd,
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

        # todo: ensure publish went without any issues
        valid = bool(context)
        if not valid:
            raise RuntimeError("Unable to publish image sequences")

