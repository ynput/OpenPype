import pyblish.api

from openpype.pipeline import OptionalPyblishPluginMixin
from openpype.pipeline.publish import RepairAction, PublishValidationError


class ValidateAlembicOptionsDefaults(
    pyblish.api.InstancePlugin, OptionalPyblishPluginMixin
):
    """Validate the attributes on the instance are defaults."""

    order = pyblish.api.ValidatorOrder
    families = ["pointcache", "animation"]
    hosts = ["maya"]
    label = "Validate Alembic Options Defaults"
    actions = [RepairAction]
    optional = True

    @classmethod
    def _get_plugin_name(self, publish_attributes):
        for key in ["ExtractAnimation", "ExtractAlembic"]:
            if key in publish_attributes.keys():
                return key

    @classmethod
    def _get_settings(self, context):
        maya_settings = context.data["project_settings"]["maya"]
        settings = maya_settings["publish"]["ExtractAlembic"]
        # Flags are a special case since they are a combination of overrides
        # and default flags from the settings.
        settings["flags"] = [
            x for x in settings["flags"] if x in settings["overrides"]
        ]
        return settings

    @classmethod
    def _get_publish_attributes(self, instance):
        attributes = instance.data["publish_attributes"][
            self._get_plugin_name(
                instance.data["publish_attributes"]
            )
        ]

        settings = self._get_settings(instance.context)

        # Flags are a special case since they are a combination of exposed
        # flags and default flags from the settings. So we need to add the
        # default flags from the settings and ensure unique items.
        non_exposed_flags = [
            x for x in settings["flags"] if x not in settings["overrides"]
        ]
        attributes["flags"] = attributes["flags"] + non_exposed_flags

        return attributes

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        settings = self._get_settings(instance.context)

        attributes = self._get_publish_attributes(instance)

        msg = (
            "Alembic Extract setting \"{}\" is not the default value:"
            "\nCurrent: {}"
            "\nDefault Value: {}\n"
        )
        errors = []
        for key, value in attributes.items():
            default_value = settings[key]

            # Lists are best to compared sorted since we cant rely on the order
            # of the items.
            if isinstance(value, list):
                value = sorted(value)
                default_value = sorted(default_value)

            if value != default_value:
                errors.append(msg.format(key, value, default_value))

        if errors:
            raise PublishValidationError("\n".join(errors))

    @classmethod
    def repair(cls, instance):
        # Find create instance twin.
        create_context = instance.context.data["create_context"]
        create_instance = None
        for Instance in create_context.instances:
            if Instance.data["instance_id"] == instance.data["instance_id"]:
                create_instance = Instance
                break

        assert create_instance is not None

        # Set the settings values on the create context then save to workfile.
        publish_attributes = instance.data["publish_attributes"]
        plugin_name = cls._get_plugin_name(publish_attributes)
        attributes = cls._get_publish_attributes(instance)
        settings = cls._get_settings(instance.context)
        create_publish_attributes = create_instance.data["publish_attributes"]
        for key in attributes.keys():
            create_publish_attributes[plugin_name][key] = settings[key]

        create_context.save_changes()
