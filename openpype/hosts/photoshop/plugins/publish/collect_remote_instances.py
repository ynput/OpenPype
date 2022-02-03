import os
import re

import pyblish.api

from openpype.lib import prepare_template_data
from openpype.lib.plugin_tools import parse_json, get_batch_asset_task_info
from openpype.hosts.photoshop import api as photoshop


class CollectRemoteInstances(pyblish.api.ContextPlugin):
    """Creates instances for configured color code of a layer.

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
        self.log.debug("mapping:: {}".format(self.color_code_mapping))

        # parse variant if used in webpublishing, comes from webpublisher batch
        batch_dir = os.environ.get("OPENPYPE_PUBLISH_DATA")
        task_data = None
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

        existing_subset_names = []
        for instance in context:
            if instance.data.get('publish'):
                existing_subset_names.append(instance.data.get('subset'))

        asset, task_name, task_type = get_batch_asset_task_info(
            task_data["context"])

        if not task_name:
            task_name = task_type

        instance_names = []
        for layer in layers:
            self.log.debug("Layer:: {}".format(layer))
            if layer.parents:
                self.log.debug("!!! Not a top layer, skip")
                continue

            resolved_family, resolved_subset_template = self._resolve_mapping(
                layer
            )
            self.log.info("resolved_family {}".format(resolved_family))
            self.log.info("resolved_subset_template {}".format(
                resolved_subset_template))

            if not resolved_subset_template or not resolved_family:
                self.log.debug("!!! Not found family or template, skip")
                continue

            fill_pairs = {
                "variant": variant,
                "family": resolved_family,
                "task": task_name,
                "layer": layer.name
            }

            subset = resolved_subset_template.format(
                **prepare_template_data(fill_pairs))

            if subset in existing_subset_names:
                self.log.info(
                    "Subset {} already created, skipping.".format(subset))
                continue

            instance = context.create_instance(layer.name)
            instance.append(layer)
            instance.data["family"] = resolved_family
            instance.data["publish"] = layer.visible
            instance.data["asset"] = asset
            instance.data["task"] = task_name
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
