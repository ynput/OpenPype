import os
import pyblish.api
from openpype.pipeline import (
    legacy_io,
    registered_host
)


class CollectWorkfile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.01
    label = "OpenRV Session Workfile"
    hosts = ['openrv']

    def process(self, context):
        """Inject the current working file"""
        host = registered_host()
        current_file = host.get_current_workfile()
        if not current_file:
            self.log.error("No current filepath detected")

        folder, file = os.path.split(current_file)
        filename, ext = os.path.splitext(file)

        task = legacy_io.Session["AVALON_TASK"]

        # create instance
        instance = context.create_instance(name=filename)
        subset = 'workfile' + task.capitalize()

        context.data['currentFile'] = current_file

        data = {}
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
