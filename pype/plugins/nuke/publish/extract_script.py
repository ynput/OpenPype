import nuke
import pyblish.api
import os


class ExtractScript(pyblish.api.InstancePlugin):
    """Publish script
    """
    label = 'Extract Script'
    order = pyblish.api.ExtractorOrder - 0.05
    hosts = ['nuke']
    families = ["script"]

    def process(self, instance):

        self.log.info('Extracting script')
        staging_dir = instance.data["stagingDir"]
        file_name = instance.data["name"]
        path = os.path.join(staging_dir, file_name)

        nuke.scriptSaveAs(path)
