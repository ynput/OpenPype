import os

import pyblish.api


class CollectWorkfile(pyblish.api.InstancePlugin):
    """Inject workfile representation into instance"""

    order = pyblish.api.CollectorOrder - 0.01
    label = "Houdini Workfile Data"
    hosts = ["houdini"]
    families = ["workfile"]

    def process(self, instance):

        current_file = instance.context.data["currentFile"]
        folder, file = os.path.split(current_file)
        filename, ext = os.path.splitext(file)

        instance.data.update({
            "setMembers": [current_file],
            "frameStart": instance.context.data['frameStart'],
            "frameEnd": instance.context.data['frameEnd'],
            "handleStart": instance.context.data['handleStart'],
            "handleEnd": instance.context.data['handleEnd']
        })

        instance.data['representations'] = [{
            'name': ext.lstrip("."),
            'ext': ext.lstrip("."),
            'files': file,
            "stagingDir": folder,
        }]

        self.log.info('Collected instance: {}'.format(file))
        self.log.info('staging Dir: {}'.format(folder))
