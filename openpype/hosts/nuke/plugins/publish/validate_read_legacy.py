import os

import nuke

import toml
import pyblish.api
from bson.objectid import ObjectId
from openpype.hosts.nuke import api as napi
from openpype.pipeline import (
    discover_loader_plugins,
    load_container,
)


class RepairReadLegacyAction(pyblish.api.Action):

    label = "Repair"
    icon = "wrench"
    on = "failed"

    def process(self, context, plugin):

        # Get the errored instances
        failed = []
        for result in context.data["results"]:
            if (result["error"] is not None and result["instance"] is not None
               and result["instance"] not in failed):
                failed.append(result["instance"])

        # Apply pyblish.logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(failed, plugin)

        for instance in instances:
            node = napi.get_instance_node(instance)
            data = toml.loads(node["avalon"].value())
            data["name"] = node.name()
            data["xpos"] = node.xpos()
            data["ypos"] = node.ypos()
            data["extension"] = os.path.splitext(
                node["file"].value()
            )[1][1:]

            data["connections"] = []
            for d in node.dependent():
                for i in range(d.inputs()):
                    if d.input(i) == node:
                        data["connections"].append([i, d])

            nuke.delete(node)

            loader_name = "LoadSequence"
            if data["extension"] == "mov":
                loader_name = "LoadMov"

            loader_plugin = None
            for Loader in discover_loader_plugins():
                if Loader.__name__ != loader_name:
                    continue

                loader_plugin = Loader

            load_container(
                Loader=loader_plugin,
                representation=ObjectId(data["representation"])
            )

            node = nuke.toNode(data["name"])
            for connection in data["connections"]:
                connection[1].setInput(connection[0], node)

            node.setXYpos(data["xpos"], data["ypos"])


class ValidateReadLegacy(pyblish.api.InstancePlugin):
    """Validate legacy read nodes."""

    order = pyblish.api.ValidatorOrder
    optional = True
    families = ["read.legacy"]
    label = "Read Legacy"
    hosts = ["nuke"]
    actions = [RepairReadLegacyAction]

    def process(self, instance):

        msg = "Clean up legacy read node \"{}\"".format(instance)
        assert False, msg
