import pyblish.api
import os
import re

from avalon import photoshop
from openpype.lib import prepare_template_data
from openpype.lib.plugin_tools import parse_json


class CollectRemoteInstances(pyblish.api.ContextPlugin):
    """Gather instances configured color code of a layer.

    Used in remote publishing when artists marks publishable layers by color-
    coding.

    Identifier:
        id (str): "pyblish.avalon.instance"
    """
    order = pyblish.api.CollectorOrder + 0.100

    label = "Instances"
    order = pyblish.api.CollectorOrder
    hosts = ["photoshop"]
    targets = ["remotepublish"]

    # configurable by Settings
    color_code_mapping = []

    def process(self, context):
        self.log.info("CollectRemoteInstances")
        self.log.info("mapping:: {}".format(self.color_code_mapping))

        # parse variant if used in webpublishing, comes from webpublisher batch
        batch_dir = os.environ.get("OPENPYPE_PUBLISH_DATA")
        variant = "Main"
        if batch_dir and os.path.exists(batch_dir):
            # TODO check if batch manifest is same as tasks manifests
            task_data = parse_json(os.path.join(batch_dir,
                                                "manifest.json"))
            if not task_data:
                raise ValueError(
                    "Cannot parse batch meta in {} folder".format(batch_dir))
            variant = task_data["variant"]

        stub = photoshop.stub()
        layers = stub.get_layers()

        instance_names = []
        for layer in layers:
            self.log.info("Layer:: {}".format(layer))
            resolved_family, resolved_subset_template = self._resolve_mapping(
                layer
            )
            self.log.info("resolved_family {}".format(resolved_family))
            self.log.info("resolved_subset_template {}".format(
                resolved_subset_template))

            if not resolved_subset_template or not resolved_family:
                self.log.debug("!!! Not marked, skip")
                continue

            if layer.parents:
                self.log.debug("!!! Not a top layer, skip")
                continue

            instance = context.create_instance(layer.name)
            instance.append(layer)
            instance.data["family"] = resolved_family
            instance.data["publish"] = layer.visible
            instance.data["asset"] = context.data["assetEntity"]["name"]
            instance.data["task"] = context.data["taskType"]

            fill_pairs = {
                "variant": variant,
                "family": instance.data["family"],
                "task": instance.data["task"],
                "layer": layer.name
            }
            subset = resolved_subset_template.format(
                **prepare_template_data(fill_pairs))
            instance.data["subset"] = subset

            instance_names.append(layer.name)

            # Produce diagnostic message for any graphical
            # user interface interested in visualising it.
            self.log.info("Found: \"%s\" " % instance.data["name"])
            self.log.info("instance: {} ".format(instance.data))

        if len(instance_names) != len(set(instance_names)):
            self.log.warning("Duplicate instances found. " +
                             "Remove unwanted via SubsetManager")

    def _resolve_mapping(self, layer):
        """Matches 'layer' color code and name to mapping.

            If both color code AND name regex is configured, BOTH must be valid
            If layer matches to multiple mappings, only first is used!
        """
        family_list = []
        family = None
        subset_name_list = []
        resolved_subset_template = None
        for mapping in self.color_code_mapping:
            if mapping["color_code"] and \
                    layer.color_code not in mapping["color_code"]:
                continue

            if mapping["layer_name_regex"] and \
                    not any(re.search(pattern, layer.name)
               for pattern in mapping["layer_name_regex"]):
                continue

            family_list.append(mapping["family"])
            subset_name_list.append(mapping["subset_template_name"])

        if len(subset_name_list) > 1:
            self.log.warning("Multiple mappings found for '{}'".
                             format(layer.name))
            self.log.warning("Only first subset name template used!")
            subset_name_list[:] = subset_name_list[0]

        if len(family_list) > 1:
            self.log.warning("Multiple mappings found for '{}'".
                             format(layer.name))
            self.log.warning("Only first family used!")
            family_list[:] = family_list[0]
        if subset_name_list:
            resolved_subset_template = subset_name_list.pop()
        if family_list:
            family = family_list.pop()

        return family, resolved_subset_template
