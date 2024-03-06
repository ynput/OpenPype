# -*- coding: utf-8 -*-
"""Collect current work file."""
import os
import pyblish.api

from pymxs import runtime as rt


class CollectWorkfile(pyblish.api.InstancePlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.01
    label = "Collect 3dsmax Workfile"
    hosts = ['max']

    def process(self, instance):
        """Inject the current working file."""
        context = instance.context
        folder = rt.maxFilePath
        file = rt.maxFileName
        if not folder or not file:
            self.log.error("Scene is not saved.")
        current_file = os.path.join(folder, file)

        context.data['currentFile'] = current_file

        ext = os.path.splitext(file)[-1].lstrip(".")

        data = {}

        # create instance
        subset = instance.data["subset"]

        data.update({
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
            "handleEnd": context.data['handleEnd']
        })

        data['representations'] = [{
            'name': ext.lstrip("."),
            'ext': ext.lstrip("."),
            'files': file,
            "stagingDir": folder,
        }]

        instance.data.update(data)
        self.log.info('Collected data: {}'.format(data))
        self.log.info('Collected instance: {}'.format(file))
        self.log.info('Scene path: {}'.format(current_file))
        self.log.info('staging Dir: {}'.format(folder))
        self.log.info('subset: {}'.format(subset))
