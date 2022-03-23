import pprint
import pyblish.api

from openpype.hosts.photoshop import api as photoshop


class CollectInstances(pyblish.api.ContextPlugin):
    """Gather instances by LayerSet and file metadata

    Collects publishable instances from file metadata or enhance
    already collected by creator (family == "image").

    Identifier:
        id (str): "pyblish.avalon.instance"
    """

    label = "Collect Instances"
    order = pyblish.api.CollectorOrder
    hosts = ["photoshop"]
    families_mapping = {
        "image": []
    }

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
        for layer_item in layer_items:
            layer_meta_data = stub.read(layer_item, layers_meta)

            # Skip layers without metadata.
            if layer_meta_data is None:
                continue

            # Skip containers.
            if "container" in layer_meta_data["id"]:
                continue

            if not layer_meta_data.get("active", True):  # active might not be in legacy meta
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
