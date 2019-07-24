
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
    families = ["workfile"]

    def process(self, instance):
        self.log.debug("instance extracting: {}".format(instance.data))
        current_script = instance.context.data["currentFile"]

        # Define extract output file path
        stagingdir = self.staging_dir(instance)
        filename = "{0}".format(instance.data["name"])
        path = os.path.join(stagingdir, filename)

        self.log.info("Performing extraction..")
        shutil.copy(current_script, path)

        if "representations" not in instance.data:
            instance.data["representations"] = list()

        representation = {
            'name': 'nk',
            'ext': '.nk',
            'files': filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '%s' to: %s" % (instance.name, path))
