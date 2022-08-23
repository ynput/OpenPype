# -*- coding: utf-8 -*-
"""Load and update RenderSetup settings.

Working with RenderSetup setting is Maya is done utilizing json files.
When this json is loaded, it will overwrite all settings on RenderSetup
instance.
"""

import json
import sys
import six

from openpype.pipeline import (
    load,
    get_representation_path
)
from openpype.hosts.maya.api import lib
from openpype.hosts.maya.api.pipeline import containerise

from maya import cmds
import maya.app.renderSetup.model.renderSetup as renderSetup


class RenderSetupLoader(load.LoaderPlugin):
    """Load json preset for RenderSetup overwriting current one."""

    families = ["rendersetup"]
    representations = ["json"]
    defaults = ['Main']

    label = "Load RenderSetup template"
    icon = "tablet"
    color = "orange"

    def load(self, context, name, namespace, data):
        """Load RenderSetup settings."""

        # from openpype.hosts.maya.api.lib import namespaced

        asset = context['asset']['name']
        namespace = namespace or lib.unique_namespace(
            asset + "_",
            prefix="_" if asset[0].isdigit() else "",
            suffix="_",
        )
        self.log.info(">>> loading json [ {} ]".format(self.fname))
        with open(self.fname, "r") as file:
            renderSetup.instance().decode(
                json.load(file), renderSetup.DECODE_AND_OVERWRITE, None)

        nodes = []
        null = cmds.sets(name="null_SET", empty=True)
        nodes.append(null)

        self[:] = nodes
        if not nodes:
            return

        self.log.info(">>> containerising [ {} ]".format(name))
        return containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__)

    def remove(self, container):
        """Remove RenderSetup settings instance."""
        from maya import cmds

        container_name = container["objectName"]

        self.log.info("Removing '%s' from Maya.." % container["name"])

        container_content = cmds.sets(container_name, query=True)
        nodes = cmds.ls(container_content, long=True)

        nodes.append(container_name)

        try:
            cmds.delete(nodes)
        except ValueError:
            # Already implicitly deleted by Maya upon removing reference
            pass

    def update(self, container, representation):
        """Update RenderSetup setting by overwriting existing settings."""
        lib.show_message(
            "Render setup update",
            "Render setup setting will be overwritten by new version. All "
            "setting specified by user not included in loaded version "
            "will be lost.")
        path = get_representation_path(representation)
        with open(path, "r") as file:
            try:
                renderSetup.instance().decode(
                    json.load(file), renderSetup.DECODE_AND_OVERWRITE, None)
            except Exception:
                self.log.error("There were errors during loading")
                six.reraise(*sys.exc_info())

        # Update metadata
        node = container["objectName"]
        cmds.setAttr("{}.representation".format(node),
                     str(representation["_id"]),
                     type="string")
        self.log.info("... updated")

    def switch(self, container, representation):
        """Switch representations."""
        self.update(container, representation)
