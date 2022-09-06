# -*- coding: utf-8 -*-
import pyblish.api
import hou


class CollectMembersAsNodes(pyblish.api.InstancePlugin):
    """Collects instance members as Houdini nodes."""

    order = pyblish.api.CollectorOrder - 0.01
    hosts = ["houdini"]
    label = "Collect Members as Nodes"

    def process(self, instance):
        if not instance.data.get("creator_identifier"):
            return

        nodes = [
            hou.node(member) for member in instance.data.get("members", [])
        ]

        instance.data["members"] = nodes
