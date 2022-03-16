import os
import re

import pyblish.api

from openpype.lib import prepare_template_data
from openpype.lib.plugin_tools import parse_json, get_batch_asset_task_info
from openpype.hosts.photoshop import api as photoshop


class CollectColorCodedInstances(pyblish.api.ContextPlugin):
    """Creates instances for configured color code of a layer.

    Used in remote publishing when artists marks publishable layers by color-
    coding.

    Can add group for all publishable layers to allow creation of flattened
    image. (Cannot contain special background layer as it cannot be grouped!)

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
    # TODO check if could be set globally, probably doesn't make sense when
    # flattened template cannot
    subset_template_name = ""
    create_flatten_image = False
    # probably not possible to configure this globally
    flatten_subset_template = ""

    def process(self, context):
        self.log.info("CollectColorCodedInstances")
        batch_dir = os.environ.get("OPENPYPE_PUBLISH_DATA")
        if (os.environ.get("IS_TEST") and
                (not batch_dir or not os.path.exists(batch_dir))):
            self.log.debug("Automatic testing, no batch data, skipping")
            return

        existing_subset_names = self._get_existing_subset_names(context)

        asset_name, task_name, variant = self._parse_batch(batch_dir)

        stub = photoshop.stub()
        layers = stub.get_layers()

        publishable_layers = []
        created_instances = []
        for layer in layers:
            self.log.debug("Layer:: {}".format(layer))
            if layer.parents:
                self.log.debug("!!! Not a top layer, skip")
                continue

            if not layer.visible:
                self.log.debug("Not visible, skip")
                continue

            resolved_family, resolved_subset_template = self._resolve_mapping(
                layer
            )

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

            instance = self._create_instance(context, layer, resolved_family,
                                             asset_name, subset, task_name)
            existing_subset_names.append(subset)
            publishable_layers.append(layer)
            created_instances.append(instance)

        if self.create_flatten_image and publishable_layers:
            self.log.debug("create_flatten_image")
            if not self.flatten_subset_template:
                self.log.warning("No template for flatten image")
                return

            fill_pairs.pop("layer")
            subset = self.flatten_subset_template.format(
                **prepare_template_data(fill_pairs))

            first_layer = publishable_layers[0]  # dummy layer
            first_layer.name = subset
            family = created_instances[0].data["family"]  # inherit family
            instance = self._create_instance(context, first_layer,
                                             family,
                                             asset_name, subset, task_name)
            instance.data["ids"] = [layer.id for layer in publishable_layers]
            created_instances.append(instance)

        for instance in created_instances:
            # Produce diagnostic message for any graphical
            # user interface interested in visualising it.
            self.log.info("Found: \"%s\" " % instance.data["name"])
            self.log.info("instance: {} ".format(instance.data))

    def _get_existing_subset_names(self, context):
        """Collect manually created instances from workfile.

        Shouldn't be any as Webpublisher bypass publishing via Openpype, but
        might be some if workfile published through OP is reused.
        """
        existing_subset_names = []
        for instance in context:
            if instance.data.get('publish'):
                existing_subset_names.append(instance.data.get('subset'))

        return existing_subset_names

    def _parse_batch(self, batch_dir):
        """Parses asset_name, task_name, variant from batch manifest."""
        task_data = None
        if batch_dir and os.path.exists(batch_dir):
            task_data = parse_json(os.path.join(batch_dir,
                                                "manifest.json"))
        if not task_data:
            raise ValueError(
                "Cannot parse batch meta in {} folder".format(batch_dir))
        variant = task_data["variant"]

        asset, task_name, task_type = get_batch_asset_task_info(
            task_data["context"])

        if not task_name:
            task_name = task_type

        return asset, task_name, variant

    def _create_instance(self, context, layer, family,
                         asset, subset, task_name):
        instance = context.create_instance(layer.name)
        instance.data["family"] = family
        instance.data["publish"] = True
        instance.data["asset"] = asset
        instance.data["task"] = task_name
        instance.data["subset"] = subset
        instance.data["layer"] = layer

        return instance

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

        self.log.debug("resolved_family {}".format(family))
        self.log.debug("resolved_subset_template {}".format(
            resolved_subset_template))
        return family, resolved_subset_template
