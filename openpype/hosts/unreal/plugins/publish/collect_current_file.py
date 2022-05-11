# -*- coding: utf-8 -*-
"""Collect current project path."""
import unreal  # noqa
import pyblish.api


class CollectUnrealCurrentFile(pyblish.api.ContextPlugin):
    """Inject the current working file into context."""

    order = pyblish.api.CollectorOrder - 0.5
    label = "Unreal Current File"
    hosts = ['unreal']

    def process(self, context):
        """Inject the current working file."""
        current_file = unreal.Paths.get_project_file_path()
        context.data['currentFile'] = current_file

        assert current_file != '', "Current file is empty. " \
            "Save the file before continuing."
