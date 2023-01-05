# -*- coding: utf-8 -*-
"""Collect information about current file."""
import os

import pyblish.api
import openpype.hosts.harmony.api as harmony


class CollectCurrentFile(pyblish.api.ContextPlugin):
    """Inject the current working file into context."""

    order = pyblish.api.CollectorOrder - 0.5
    label = "Current File"
    hosts = ["harmony"]

    def process(self, context):
        """Inject the current working file."""
        self_name = self.__class__.__name__

        current_file = harmony.send(
            {"function": f"PypeHarmony.Publish.{self_name}.collect"})["result"]
        context.data["currentFile"] = os.path.normpath(current_file)
