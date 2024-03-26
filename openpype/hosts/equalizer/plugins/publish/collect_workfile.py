# -*- coding: utf-8 -*-
"""Collect current work file."""
from pathlib import Path

import pyblish.api
import tde4


class CollectWorkfile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.01
    label = "Collect 3DE4 Workfile"
    hosts = ['equalizer']

    def process(self, context: pyblish.api.Context):
        """Inject the current working file."""
        project_file = Path(tde4.getProjectPath())
        current_file = project_file.as_posix()

        context.data['currentFile'] = current_file

        filename = project_file.stem
        ext = project_file.suffix

        task = context.data["task"]

        data = {}

        # create instance
        instance = context.create_instance(name=filename)
        subset = f'workfile{task.capitalize()}'

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
                    "files": project_file.name,
                    "stagingDir": project_file.parent.as_posix(),
                }
            ]
        }

        instance.data.update(data)

        self.log.info(f'Collected instance: {project_file.name}')
        self.log.info(f'Scene path: {current_file}')
        self.log.info(f'staging Dir: {project_file.parent.as_posix()}')
        self.log.info(f'subset: {subset}')
