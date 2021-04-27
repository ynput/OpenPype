import pyblish.api
import avalon.api

from avalon import photoshop


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
    # True will add all instances to same group in Loader
    group_by_task_name = False

    def process(self, context):
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

            if self.group_by_task_name:
                task = avalon.api.Session["AVALON_TASK"]
                sanitized_task_name = task[0].upper() + task[1:]
                instance.data["subsetGroup"] = sanitized_task_name

            instance_names.append(layer_data["subset"])

            # Produce diagnostic message for any graphical
            # user interface interested in visualising it.
            self.log.info("Found: \"%s\" " % instance.data["name"])
            self.log.info("instance: {} ".format(instance.data))

        if len(instance_names) != len(set(instance_names)):
            self.log.warning("Duplicate instances found. " +
                             "Remove unwanted via SubsetManager")
