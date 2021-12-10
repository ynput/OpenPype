import pyblish.api
import avalon.api
import os
from maya import cmds


class CollectWorkfile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.01
    label = "Maya Workfile"
    hosts = ['maya']

    def process(self, context):
        """Inject the current working file"""
        current_file = cmds.file(query=True, sceneName=True)
        context.data['currentFile'] = current_file

        folder, file = os.path.split(current_file)
        filename, ext = os.path.splitext(file)

        task = avalon.api.Session["AVALON_TASK"]

        data = {}

        families_whitelist = os.getenv("PYBLISH_FAMILY_WHITELIST")
        if families_whitelist:
            families_whitelist = families_whitelist.split(',')
        if families_whitelist:
            if 'workfile' not in families_whitelist:
                self.log.info("Skipped instance with not whitelisted "
                              "family: {}".format('workfile'))
                return

        # create instance
        instance = context.create_instance(name=filename)
        subset = 'workfile' + task.capitalize()

        data.update({
            "subset": subset,
            "asset": os.getenv("AVALON_ASSET", None),
            "label": subset,
            "publish": True,
            "family": 'workfile',
            "families": ['workfile'],
            "setMembers": [current_file],
            "frameStart": context.data['frameStart'],
            "frameEnd": context.data['frameEnd'],
            "handleStart": context.data['handleStart'],
            "handleEnd": context.data['handleEnd']
        })

        data['representations'] = [{
            'name': ext.lstrip("."),
            'ext': ext.lstrip("."),
            'files': file,
            "stagingDir": folder,
        }]

        instance.data.update(data)

        self.log.info('Collected instance: {}'.format(file))
        self.log.info('Scene path: {}'.format(current_file))
        self.log.info('staging Dir: {}'.format(folder))
        self.log.info('subset: {}'.format(subset))
