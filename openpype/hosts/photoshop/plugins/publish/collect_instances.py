import pprint
import pyblish.api

from openpype.hosts.photoshop import api as photoshop


class CollectInstances(pyblish.api.ContextPlugin):
    """Gather instances by LayerSet and file metadata

    This collector takes into account assets that are associated with
    an LayerSet and marked with a unique identifier;

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
            if instance.data["family"] == "image" and instance.data.get("members"):
                instance_by_layer_id[str(instance.data["members"][0])] = instance

        stub = photoshop.stub()
        layers = stub.get_layers()
        layers_meta = stub.get_layers_metadata()
        instance_names = []
        for layer in layers:
            layer_data = stub.read(layer, layers_meta)

            # Skip layers without metadata.
            if layer_data is None:
                continue

            # Skip containers.
            if "container" in layer_data["id"]:
                continue

            instance = instance_by_layer_id.get(str(layer.id))
            if instance is None:
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
            self.log.info("instance: {} ".format(pprint.pformat(instance.data, indent=4)))

        if len(instance_names) != len(set(instance_names)):
            self.log.warning("Duplicate instances found. " +
                             "Remove unwanted via SubsetManager")
