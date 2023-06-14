import pyblish.api

from openpype.pipeline.publish import (
    ValidateContentsOrder,
    PublishXmlValidationError,
    OptionalPyblishPluginMixin,
    RepairAction,
)


class ValidateExistingVersion(
    OptionalPyblishPluginMixin,
    pyblish.api.InstancePlugin
):
    label = "Validate Existing Version"
    order = ValidateContentsOrder

    hosts = ["traypublisher"]

    actions = [RepairAction]

    settings_category = "traypublisher"
    optional = True

    def process(self, instance):
        version = instance.data.get("version")
        if version is None:
            return

        last_version = instance.data.get("latestVersion")
        if last_version is None or last_version < version:
            return

        subset_name = instance.data["subset"]
        msg = "Version {} already exists for subset {}.".format(
            version, subset_name)

        formatting_data = {
            "subset_name": subset_name,
            "asset_name": instance.data["asset"],
            "version": version
        }
        raise PublishXmlValidationError(
            self, msg, formatting_data=formatting_data)

    @classmethod
    def repair(cls, instance):
        create_context = instance.context.data["create_context"]
        created_instance = create_context.get_instance_by_id(
            instance.data["instance_id"])
        creator_attributes = created_instance["creator_attributes"]
        # Disable version override
        creator_attributes["use_next_version"] = True
        create_context.save_changes()
