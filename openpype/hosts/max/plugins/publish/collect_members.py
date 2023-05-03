# -*- coding: utf-8 -*-
"""Collect instance members"""
import pyblish.api
from pymxs import runtime as rt


class CollectMembers(pyblish.api.InstancePlugin):
    """Collect Render for Deadline"""

    order = pyblish.api.CollectorOrder + 0.01
    label = "Collect Instance Members"
    hosts = ['max']

    def process(self, instance):

        if instance.data.get("instance_node"):
            container = rt.GetNodeByName(instance.data["instance_node"])
            instance.data["members"] = [i.node for i in container.openPypeData.all_handles]
