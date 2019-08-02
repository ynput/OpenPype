import toml

import nuke

import pyblish.api


class CollectReadLegacy(pyblish.api.ContextPlugin):
    """Collect legacy read nodes."""

    order = pyblish.api.CollectorOrder
    label = "Collect Read Legacy"
    hosts = ["nuke", "nukeassist"]

    def process(self, context):

        for node in nuke.allNodes():
            if node.Class() != "Read":
                continue

            if "avalon" not in node.knobs().keys():
                continue

            if not toml.loads(node["avalon"].value()):
                return

            instance = context.create_instance(
                node.name(), family="read.legacy"
            )
            instance.append(node)
