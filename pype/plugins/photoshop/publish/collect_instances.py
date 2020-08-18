import pythoncom

from avalon import photoshop

import pyblish.api

from pype.modules.websocket_server.clients.photoshop_client import PhotoshopClientStub

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
        # Necessary call when running in a different thread which pyblish-qml
        # can be.
        pythoncom.CoInitialize()

        from datetime import datetime
        start = datetime.now()
        # for timing
        photoshop_client = PhotoshopClientStub()
        layers = photoshop_client.get_layers()
        for layer in layers:
            layer_data = photoshop_client.read(layer)

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

            instance = context.create_instance(layer.name)
            instance.append(layer)
            instance.data.update(layer_data)
            instance.data["families"] = self.families_mapping[
                layer_data["family"]
            ]
            instance.data["publish"] = layer.visible

            # Produce diagnostic message for any graphical
            # user interface interested in visualising it.
            self.log.info("Found: \"%s\" " % instance.data["name"])
