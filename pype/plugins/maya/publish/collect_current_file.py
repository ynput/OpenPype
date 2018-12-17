from maya import cmds

import pyblish.api
import os
from pype.maya import lib


class CollectMayaCurrentFile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.5
    label = "Maya Current File"
    hosts = ['maya']

    def process(self, context):
        """Inject the current working file"""
        current_file = cmds.file(query=True, sceneName=True)
        context.data['currentFile'] = current_file

        folder, file = os.path.split(current_file)
        filename, ext = os.path.splitext(file)

        data = {}

        for key, value in lib.collect_animation_data().items():
            data[key] = value

        # create instance
        instance = context.create_instance(name=filename)

        data.update({
            "subset": filename,
            "asset": os.getenv("AVALON_ASSET", None),
            "label": file,
            "publish": True,
            "family": 'scene',
            "representation": "ma",
            "setMembers": [current_file],
            "stagingDir": folder
        })

        data['files'] = [file]

        instance.data.update(data)

        self.log.info('Collected instance: {}'.format(file))
        self.log.info('Scene path: {}'.format(current_file))
        self.log.info('stagin Dir: {}'.format(folder))
        self.log.info('subset: {}'.format(filename))
