import pyblish.api
from openpype.pipeline import PublishXmlValidationError
from openpype.hosts.tvpaint.api import pipeline


class FixAssetNames(pyblish.api.Action):
    """Repair the asset names.

    Change instanace metadata in the workfile.
    """

    label = "Repair"
    icon = "wrench"
    on = "failed"

    def process(self, context, plugin):
        context_asset_name = context.data["asset"]
        old_instance_items = pipeline.list_instances()
        new_instance_items = []
        for instance_item in old_instance_items:
            instance_asset_name = instance_item.get("asset")
            if (
                instance_asset_name
                and instance_asset_name != context_asset_name
            ):
                instance_item["asset"] = context_asset_name
            new_instance_items.append(instance_item)
        pipeline._write_instances(new_instance_items)


class ValidateAssetNames(pyblish.api.ContextPlugin):
    """Validate assset name present on instance.

    Asset name on instance should be the same as context's.
    """

    label = "Validate Asset Names"
    order = pyblish.api.ValidatorOrder
    hosts = ["tvpaint"]
    actions = [FixAssetNames]

    def process(self, context):
        context_asset_name = context.data["asset"]
        for instance in context:
            asset_name = instance.data.get("asset")
            if asset_name and asset_name == context_asset_name:
                continue

            instance_label = (
                instance.data.get("label") or instance.data["name"]
            )

            raise PublishXmlValidationError(
                self,
                (
                    "Different asset name on instance then context's."
                    " Instance \"{}\" has asset name: \"{}\""
                    " Context asset name is: \"{}\""
                ).format(
                    instance_label, asset_name, context_asset_name
                ),
                formatting_data={
                    "expected_asset": context_asset_name,
                    "found_asset": asset_name
                }
            )
