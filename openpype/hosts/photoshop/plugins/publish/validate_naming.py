import re

import pyblish.api
import openpype.api
from openpype.hosts.photoshop import api as photoshop


class ValidateNamingRepair(pyblish.api.Action):
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

        invalid_chars, replace_char = plugin.get_replace_chars()
        self.log.info("{} --- {}".format(invalid_chars, replace_char))

        # Apply pyblish.logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(failed, plugin)
        stub = photoshop.stub()
        for instance in instances:
            self.log.info("validate_naming instance {}".format(instance))
            layer_item = instance.data["layer"]
            metadata = stub.read(layer_item)
            self.log.info("metadata instance {}".format(metadata))
            layer_name = None
            if metadata.get("uuid"):
                layer_data = stub.get_layer(metadata["uuid"])
                self.log.info("layer_data {}".format(layer_data))
                if layer_data:
                    layer_name = re.sub(invalid_chars,
                                        replace_char,
                                        layer_data.name)

                    stub.rename_layer(instance.data["uuid"], layer_name)

            subset_name = re.sub(invalid_chars, replace_char,
                                 instance.data["subset"])

            layer_item.name = layer_name or subset_name
            metadata["subset"] = subset_name
            stub.imprint(layer_item, metadata)

        return True


class ValidateNaming(pyblish.api.InstancePlugin):
    """Validate the instance name.

    Spaces in names are not allowed. Will be replace with underscores.
    """

    label = "Validate Naming"
    hosts = ["photoshop"]
    order = openpype.api.ValidateContentsOrder
    families = ["image"]
    actions = [ValidateNamingRepair]

    # configured by Settings
    invalid_chars = ''
    replace_char = ''

    def process(self, instance):
        help_msg = ' Use Repair action (A) in Pyblish to fix it.'
        msg = "Name \"{}\" is not allowed.{}".format(instance.data["name"],
                                                     help_msg)
        assert not re.search(self.invalid_chars, instance.data["name"]), msg

        msg = "Subset \"{}\" is not allowed.{}".format(instance.data["subset"],
                                                       help_msg)
        assert not re.search(self.invalid_chars, instance.data["subset"]), msg

    @classmethod
    def get_replace_chars(cls):
        """Pass values configured in Settings for Repair."""
        return cls.invalid_chars, cls.replace_char
