import pyblish.api
import os

from avalon import photoshop
from openpype.lib import prepare_template_data


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

    # configurable by Settings
    families = ["background"]
    color_code = ["red"]
    subset_template_name = ""

    def process(self, context):
        self.log.info("CollectRemoteInstances")
        if not os.environ.get("IS_HEADLESS"):
            self.log.debug("Not headless publishing, skipping.")
            return

        # parse variant if used in webpublishing, comes from webpublisher batch
        batch_dir = os.environ.get("OPENPYPE_PUBLISH_DATA")
        variant = "Main"
        if batch_dir and os.path.exists(batch_dir):
            # TODO check if batch manifest is same as tasks manifests
            task_data = self.parse_json(os.path.join(batch_dir,
                                                     "manifest.json"))
            variant = task_data["variant"]

        stub = photoshop.stub()
        layers = stub.get_layers()

        instance_names = []
        for layer in layers:
            self.log.info("!!!Layer:: {}".format(layer))
            if layer.color_code not in self.color_code:
                self.log.debug("Not marked, skip")
                continue

            if layer.parents:
                self.log.debug("Not a top layer, skip")
                continue

            instance = context.create_instance(layer.name)
            instance.append(layer)
            instance.data["family"] = self.families[0]
            instance.data["publish"] = layer.visible

            # populate data from context, coming from outside?? TODO
            # TEMP
            self.log.info("asset {}".format(context.data["assetEntity"]))
            self.log.info("taskType {}".format(context.data["taskType"]))
            instance.data["asset"] = context.data["assetEntity"]["name"]
            instance.data["task"] = context.data["taskType"]

            fill_pairs = {
                "variant": variant,
                "family": instance.data["family"],
                "task": instance.data["task"],
                "layer": layer.name
            }
            subset = self.subset_template.format(
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
