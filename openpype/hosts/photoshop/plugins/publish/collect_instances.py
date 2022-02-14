import os

import pyblish.api

from openpype.hosts.photoshop import api as photoshop


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

    def process(self, context):
        stub = photoshop.stub()
        layers = stub.get_layers()
        layers_meta = stub.get_layers_metadata()
        instance_names = []

        families_whitelist = os.getenv("PYBLISH_FAMILY_WHITELIST")
        if families_whitelist:
            families_whitelist = families_whitelist.split(',')

        for layer in layers:
            layer_data = stub.read(layer, layers_meta)

            # Skip layers without metadata.
            if layer_data is None:
                continue

            # Skip containers.
            if "container" in layer_data["id"]:
                continue

            if families_whitelist:
                if layer_data["family"] not in families_whitelist:
                    self.log.info("Skipped instance with not whitelisted "
                                  "family: {}".format(layer_data["family"]))
                    continue

            # child_layers = [*layer.Layers]
            # self.log.debug("child_layers {}".format(child_layers))
            # if not child_layers:
            #     self.log.info("%s skipped, it was empty." % layer.Name)
            #     continue

            instance = context.create_instance(layer_data["subset"])
            instance.append(layer)
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
