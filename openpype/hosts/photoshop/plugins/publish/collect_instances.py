import pprint
from avalon import api
import pyblish.api

from openpype.settings import get_project_settings
from openpype.hosts.photoshop import api as photoshop
from openpype.lib import prepare_template_data


class CollectInstances(pyblish.api.ContextPlugin):
    """Gather instances by LayerSet and file metadata

    Collects publishable instances from file metadata or enhance
    already collected by creator (family == "image").

    If no image instances are explicitly created, it looks if there is value
    in `flatten_subset_template` (configurable in Settings), in that case it
    produces flatten image with all visible layers.

    Identifier:
        id (str): "pyblish.avalon.instance"
    """

    label = "Collect Instances"
    order = pyblish.api.CollectorOrder
    hosts = ["photoshop"]
    families_mapping = {
        "image": []
    }
    # configurable in Settings
    flatten_subset_template = ""

    def process(self, context):
        instance_by_layer_id = {}
        for instance in context:
            if (
                    instance.data["family"] == "image" and
                    instance.data.get("members")):
                layer_id = str(instance.data["members"][0])
                instance_by_layer_id[layer_id] = instance

        stub = photoshop.stub()
        layer_items = stub.get_layers()
        layers_meta = stub.get_layers_metadata()
        instance_names = []

        all_layer_ids = []
        for layer_item in layer_items:
            layer_meta_data = stub.read(layer_item, layers_meta)
            all_layer_ids.append(layer_item.id)

            # Skip layers without metadata.
            if layer_meta_data is None:
                continue

            # Skip containers.
            if "container" in layer_meta_data["id"]:
                continue

            # active might not be in legacy meta
            if not layer_meta_data.get("active", True):
                continue

            instance = instance_by_layer_id.get(str(layer_item.id))
            if instance is None:
                instance = context.create_instance(layer_meta_data["subset"])

            instance.data["layer"] = layer_item
            instance.data.update(layer_meta_data)
            instance.data["families"] = self.families_mapping[
                layer_meta_data["family"]
            ]
            instance.data["publish"] = layer_item.visible
            instance_names.append(layer_meta_data["subset"])

            # Produce diagnostic message for any graphical
            # user interface interested in visualising it.
            self.log.info("Found: \"%s\" " % instance.data["name"])
            self.log.info("instance: {} ".format(
                pprint.pformat(instance.data, indent=4)))

        if len(instance_names) != len(set(instance_names)):
            self.log.warning("Duplicate instances found. " +
                             "Remove unwanted via SubsetManager")

        if len(instance_names) == 0 and self.flatten_subset_template:
            project_name = context.data["projectEntity"]["name"]
            variants = get_project_settings(project_name).get(
                "photoshop", {}).get(
                "create", {}).get(
                "CreateImage", {}).get(
                "defaults", [''])
            family = "image"
            task_name = api.Session["AVALON_TASK"]
            asset_name = context.data["assetEntity"]["name"]

            variant = context.data.get("variant") or variants[0]
            fill_pairs = {
                "variant": variant,
                "family": family,
                "task": task_name
            }

            subset = self.flatten_subset_template.format(
                **prepare_template_data(fill_pairs))

            instance = context.create_instance(subset)
            instance.data["family"] = family
            instance.data["asset"] = asset_name
            instance.data["subset"] = subset
            instance.data["ids"] = all_layer_ids
            instance.data["families"] = self.families_mapping[family]
            instance.data["publish"] = True

            self.log.info("flatten instance: {} ".format(instance.data))
