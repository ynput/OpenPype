# -*- coding: utf-8 -*-
"""Load template."""
import tempfile
import zipfile
import os
import shutil
import uuid

from avalon import api
import openpype.hosts.harmony.api as harmony
import openpype.lib


class TemplateLoader(api.Loader):
    """Load Harmony template as container.

    .. todo::

        This must be implemented properly.

    """

    families = ["template", "workfile"]
    representations = ["*"]
    label = "Load Template"
    icon = "gift"

    def load(self, context, name=None, namespace=None, data=None):
        """Plugin entry point.

        Args:
            context (:class:`pyblish.api.Context`): Context.
            name (str, optional): Container name.
            namespace (str, optional): Container namespace.
            data (dict, optional): Additional data passed into loader.

        """
        # Load template.
        self_name = self.__class__.__name__
        temp_dir = tempfile.mkdtemp()
        zip_file = api.get_representation_path(context["representation"])
        template_path = os.path.join(temp_dir, "temp.tpl")
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(template_path)

        group_id = "{}".format(uuid.uuid4())

        container_group = harmony.send(
            {
                "function": f"PypeHarmony.Loaders.{self_name}.loadContainer",
                "args": [template_path,
                         context["asset"]["name"],
                         context["subset"]["name"],
                         group_id]
            }
        )["result"]

        # Cleanup the temp directory
        shutil.rmtree(temp_dir)

        # We must validate the group_node
        return harmony.containerise(
            name,
            namespace,
            container_group,
            context,
            self_name
        )

    def update(self, container, representation):
        """Update loaded containers.

        Args:
            container (dict): Container data.
            representation (dict): Representation data.

        """
        node_name = container["name"]
        node = harmony.find_node_by_name(node_name, "GROUP")
        self_name = self.__class__.__name__

        update_and_replace = False
        if openpype.lib.is_latest(representation):
            self._set_green(node)
        else:
            self._set_red(node)

        update_and_replace = harmony.send(
            {
                "function": f"PypeHarmony.Loaders.{self_name}."
                            "askForColumnsUpdate",
                "args": []
            }
        )["result"]

        if update_and_replace:
            # FIXME: This won't work, need to implement it.
            harmony.send(
                {
                    "function": f"PypeHarmony.Loaders.{self_name}."
                                "replaceNode",
                    "args": []
                }
            )
        else:
            self.load(
                container["context"], container["name"],
                None, container["data"])

        harmony.imprint(
            node, {"representation": str(representation["_id"])}
        )

    def remove(self, container):
        """Remove container.

        Args:
            container (dict): container definition.

        """
        node = harmony.find_node_by_name(container["name"], "GROUP")
        harmony.send(
            {"function": "PypeHarmony.deleteNode", "args": [node]}
        )

    def switch(self, container, representation):
        """Switch representation containers."""
        self.update(container, representation)

    def _set_green(self, node):
        """Set node color to green `rgba(0, 255, 0, 255)`."""
        harmony.send(
            {
                "function": "PypeHarmony.setColor",
                "args": [node, [0, 255, 0, 255]]
            })

    def _set_red(self, node):
        """Set node color to red `rgba(255, 0, 0, 255)`."""
        harmony.send(
            {
                "function": "PypeHarmony.setColor",
                "args": [node, [255, 0, 0, 255]]
            })
