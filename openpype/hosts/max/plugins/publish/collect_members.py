# -*- coding: utf-8 -*-
"""Collect instance members."""
import pyblish.api
from pymxs import runtime as rt
from openpype.hosts.max.api.lib import get_tyflow_export_operators


class CollectMembers(pyblish.api.InstancePlugin):
    """Collect Set Members."""

    order = pyblish.api.CollectorOrder + 0.01
    label = "Collect Instance Members"
    hosts = ['max']

    def process(self, instance):
        if instance.data["productType"] in {"workfile", "tyflow"}:
            self.log.debug(
                "Skipping Collecting Members for workfile "
                "and tyflow product type."
            )
            return
        if instance.data["productType"] in {"tycache", "tyspline"}:
            instance.data["operator"] = next(
                (node for node in get_tyflow_export_operators()
                 if node.name == instance.data["productName"]), None)   # noqa
            self.log.debug("operator: {}".format(instance.data["operator"]))

        elif instance.data.get("instance_node"):
            container = rt.GetNodeByName(instance.data["instance_node"])
            instance.data["members"] = [
                member.node for member
                in container.modifiers[0].openPypeData.all_handles
            ]
