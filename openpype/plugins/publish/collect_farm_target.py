# -*- coding: utf-8 -*-
import pyblish.api


class CollectFarmTarget(pyblish.api.InstancePlugin):
    """Collects the render target for the instance
    """

    order = pyblish.api.CollectorOrder + 0.499
    label = "Collect Farm Target"
    targets = ["local"]

    def process(self, instance):
        if not instance.data.get("farm"):
            return

        context = instance.context

        farm_name = ""
        op_modules = context.data.get("openPypeModules")

        for farm_renderer in ["deadline", "royalrender"]:
            op_module = op_modules.get(farm_renderer, False)

            if op_module and op_module.enabled:
                farm_name = farm_renderer
            elif not op_module:
                self.log.error("Cannot get OpenPype {0} module.".format(
                    farm_renderer))

        if farm_name:
            self.log.debug("Collected render target: {0}".format(farm_name))
            instance.data["toBeRenderedOn"] = farm_name
        else:
            AssertionError("No OpenPype renderer module found")
