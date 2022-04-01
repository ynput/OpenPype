from avalon import api
import pyblish.api

from openpype.settings import get_project_settings
from openpype.hosts.photoshop import api as photoshop
from openpype.lib import prepare_template_data


class CollectInstances(pyblish.api.ContextPlugin):
    """Gather instances by LayerSet and file metadata

    This collector takes into account assets that are associated with
    an LayerSet and marked with a unique identifier;

    Identifier:
        id (str): "pyblish.avalon.instance"
    """

    label = "Instances"
    order = pyblish.api.CollectorOrder
    hosts = ["photoshop"]
    families_mapping = {
        "image": []
    }
    flatten_subset_template = ""

    def process(self, context):
        stub = photoshop.stub()
        layers = stub.get_layers()
        layers_meta = stub.get_layers_metadata()
        instance_names = []
        all_layer_ids = []
        for layer in layers:
            all_layer_ids.append(layer.id)
            layer_data = stub.read(layer, layers_meta)

            # Skip layers without metadata.
            if layer_data is None:
                continue

            # Skip containers.
            if "container" in layer_data["id"]:
                continue

            # child_layers = [*layer.Layers]
            # self.log.debug("child_layers {}".format(child_layers))
            # if not child_layers:
            #     self.log.info("%s skipped, it was empty." % layer.Name)
            #     continue

            instance = context.create_instance(layer_data["subset"])
            instance.data["layer"] = layer
            instance.data.update(layer_data)
            instance.data["families"] = self.families_mapping[
                layer_data["family"]
            ]
            instance.data["publish"] = layer.visible
            instance_names.append(layer_data["subset"])

            # Produce diagnostic message for any graphical
            # user interface interested in visualising it.
            self.log.info("Found: \"%s\" " % instance.data["name"])
            self.log.info("instance: {} ".format(instance.data))

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

            fill_pairs = {
                "variant": variants[0],
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
