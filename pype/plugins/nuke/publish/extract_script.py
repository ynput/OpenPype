
import pyblish.api
import os
import pype
import shutil


class ExtractScript(pype.api.Extractor):
    """Publish script
    """
    label = 'Extract Script'
    order = pyblish.api.ExtractorOrder - 0.05
    optional = True
    hosts = ['nuke']
    families = ["nukescript"]

    def process(self, instance):
        self.log.debug("instance extracting: {}".format(instance.data))
        current_script = instance.context.data["currentFile"]

        # Define extract output file path
        dir_path = self.staging_dir(instance)
        filename = "{0}".format(instance.data["name"])
        path = os.path.join(dir_path, filename)

        self.log.info("Performing extraction..")
        shutil.copy(current_script, path)

        if "files" not in instance.data:
            instance.data["files"] = list()

        instance.data["files"].append(filename)

        self.log.info("Extracted instance '%s' to: %s" % (instance.name, path))
