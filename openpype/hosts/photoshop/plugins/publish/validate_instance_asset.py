import pyblish.api

from openpype.pipeline import get_current_asset_name
from openpype.pipeline.publish import (
    ValidateContentsOrder,
    PublishXmlValidationError,
    OptionalPyblishPluginMixin
)
from openpype.hosts.photoshop import api as photoshop


class ValidateInstanceAssetRepair(pyblish.api.Action):
    """Repair the instance asset."""

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
        stub = photoshop.stub()
        current_asset_name = get_current_asset_name()
        for instance in instances:
            data = stub.read(instance[0])
            data["asset"] = current_asset_name
            stub.imprint(instance[0], data)


class ValidateInstanceAsset(OptionalPyblishPluginMixin,
                            pyblish.api.InstancePlugin):
    """Validate the instance asset is the current selected context asset.

    As it might happen that multiple worfiles are opened, switching
    between them would mess with selected context.
    In that case outputs might be output under wrong asset!

    Repair action will use Context asset value (from Workfiles or Launcher)
    Closing and reopening with Workfiles will refresh  Context value.
    """

    label = "Validate Instance Asset"
    hosts = ["photoshop"]
    optional = True
    actions = [ValidateInstanceAssetRepair]
    order = ValidateContentsOrder

    def process(self, instance):
        instance_asset = instance.data["asset"]
        current_asset = get_current_asset_name()

        if instance_asset != current_asset:
            msg = (
                f"Instance asset {instance_asset} is not the same "
                f"as current context {current_asset}."

            )
            repair_msg = (
                f"Repair with 'Repair' button to use '{current_asset}'.\n"
            )
            formatting_data = {"msg": msg,
                               "repair_msg": repair_msg}
            raise PublishXmlValidationError(self, msg,
                                            formatting_data=formatting_data)
