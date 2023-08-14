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

        try:
            royalrender_module = \
                context.data.get("openPypeModules")["royalrender"]
            instance.data["toBeRenderedOn"] = "royalrender"
            self.log.debug("Collected render target: royalrender")
        except AttributeError:
            self.log.error("Cannot get OpenPype RoyalRender module.")
            raise AssertionError("OpenPype RoyalRender module not found.")

        try:
            muster_module = context.data.get("openPypeModules")["muster"]
            instance.data["toBeRenderedOn"] = "muster"
            self.log.debug("Collected render target: muster")
        except AttributeError:
            self.log.error("Cannot get OpenPype Muster module.")
            raise AssertionError("OpenPype Muster module not found.")
