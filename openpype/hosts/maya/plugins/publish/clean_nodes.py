# -*- coding: utf-8 -*-
"""Cleanup leftover nodes."""
from maya import cmds  # noqa
import pyblish.api


class CleanNodesUp(pyblish.api.InstancePlugin):
    """Cleans up the staging directory after a successful publish.

    This will also clean published renders and delete their parent directories.

    """

    order = pyblish.api.IntegratorOrder + 10
    label = "Clean Nodes"
    optional = True
    active = True

    def process(self, instance):
        if not instance.data.get("cleanNodes"):
            self.log.info("Nothing to clean.")
            return

        nodes_to_clean = instance.data.pop("cleanNodes", [])
        self.log.info("Removing {} nodes".format(len(nodes_to_clean)))
        for node in nodes_to_clean:
            try:
                cmds.delete(node)
            except ValueError:
                # object might be already deleted, don't complain about it
                pass
