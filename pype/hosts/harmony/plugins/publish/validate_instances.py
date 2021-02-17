import os

import pyblish.api
import pype.api
from avalon import harmony


class ValidateInstanceRepair(pyblish.api.Action):
    """Repair the instance."""

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
            data = harmony.read(instance[0])
            data["asset"] = os.environ["AVALON_ASSET"]
            harmony.imprint(instance[0], data)


class ValidateInstance(pyblish.api.InstancePlugin):
    """Validate the instance asset is the current asset."""

    label = "Validate Instance"
    hosts = ["harmony"]
    actions = [ValidateInstanceRepair]
    order = pype.api.ValidateContentsOrder

    def process(self, instance):
        instance_asset = instance.data["asset"]
        current_asset = os.environ["AVALON_ASSET"]
        msg = (
            "Instance asset is not the same as current asset:"
            f"\nInstance: {instance_asset}\nCurrent: {current_asset}"
        )
        assert instance_asset == current_asset, msg
