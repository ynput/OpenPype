# -*- coding: utf-8 -*-
import pyblish.api


class CollectFarmTargetInstance(pyblish.api.InstancePlugin):
    """Collects the render target for the instance
    """

    order = pyblish.api.CollectorOrder + 0.499
    label = "Collect Farm Target"
    targets = ["local"]

    def process(self, instance):
        if not instance.data.get("farm"):
            return

        context = instance.context
        try:
            deadline_module = context.data.get("openPypeModules")["deadline"]
            instance.data["toBeRenderedOn"] = "deadline"
            self.log.debug("Collected render target: deadline")
        except AttributeError:
            self.log.error("Cannot get OpenPype Deadline module.")
            raise AssertionError("OpenPype Deadline module not found.")
