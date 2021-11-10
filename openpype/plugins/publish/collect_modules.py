# -*- coding: utf-8 -*-
"""Collect OpenPype modules."""
from openpype.modules import ModulesManager
import pyblish.api


class CollectModules(pyblish.api.ContextPlugin):
    """Collect OpenPype modules."""

    order = pyblish.api.CollectorOrder - 0.45
    label = "OpenPype Modules"

    def process(self, context):
        manager = ModulesManager()
        context.data["openPypeModules"] = manager.modules_by_name
