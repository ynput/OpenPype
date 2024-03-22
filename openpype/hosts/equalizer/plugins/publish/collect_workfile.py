# -*- coding: utf-8 -*-
"""Collect current work file."""
import os
import pyblish.api
import tde4

class CollectWorkfile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.01
    label = "Collect 3DE4 Workfile"
    hosts = ['equalizer']

    def process(self, context):
        """Inject the current working file."""
        project_file = tde4.getProjectPath()
        current_file = os.path.normpath(project_file)

        context.data['currentFile'] = current_file

        filename = os.path.splitext(os.path.basename(project_file))[0]
        ext = os.path.splitext(project_file)[1]

        task = context.data["task"]

        data = {}

        # create instance
        instance = context.create_instance(name=filename)
        subset = 'workfile{}'.format(task.capitalize())

        data = {
            "subset": subset,
            "asset": context.data["asset"],
            "label": subset,
            "publish": True,
            "family": 'workfile',
            "families": ['workfile'],
            "setMembers": [current_file],
            "frameStart": context.data['frameStart'],
            "frameEnd": context.data['frameEnd'],
            "handleStart": context.data['handleStart'],
            "handleEnd": context.data['handleEnd'],
            "representations": [
                {
                    "name": ext.lstrip("."),
                    "ext": ext.lstrip("."),
                    "files": os.path.basename(project_file),
                    "stagingDir": os.path.dirname(project_file),
                }
            ]
        }

        instance.data.update(data)

        self.log.info('Collected instance: {}'.format(os.path.basename(project_file)))
        self.log.info('Scene path: {}'.format(current_file))
        self.log.info('staging Dir: {}'.format(os.path.dirname(project_file)))
        self.log.info('subset: {}'.format(subset))
