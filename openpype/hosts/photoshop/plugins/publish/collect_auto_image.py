import pyblish.api

from openpype.client import get_asset_name_identifier
from openpype.hosts.photoshop import api as photoshop
from openpype.pipeline.create import get_subset_name


class CollectAutoImage(pyblish.api.ContextPlugin):
    """Creates auto image in non artist based publishes (Webpublisher).
    """

    label = "Collect Auto Image"
    order = pyblish.api.CollectorOrder
    hosts = ["photoshop"]
    order = pyblish.api.CollectorOrder + 0.2

    targets = ["automated"]

    def process(self, context):
        for instance in context:
            creator_identifier = instance.data.get("creator_identifier")
            if creator_identifier and creator_identifier == "auto_image":
                self.log.debug("Auto image instance found, won't create new")
                return

        project_name = context.data["projectName"]
        proj_settings = context.data["project_settings"]
        task_name = context.data["task"]
        host_name = context.data["hostName"]
        asset_doc = context.data["assetEntity"]
        asset_name = get_asset_name_identifier(asset_doc)

        auto_creator = proj_settings.get(
            "photoshop", {}).get(
            "create", {}).get(
            "AutoImageCreator", {})

        if not auto_creator or not auto_creator["enabled"]:
            self.log.debug("Auto image creator disabled, won't create new")
            return

        stub = photoshop.stub()
        stored_items = stub.get_layers_metadata()
        for item in stored_items:
            if item.get("creator_identifier") == "auto_image":
                if not item.get("active"):
                    self.log.debug("Auto_image instance disabled")
                    return

        layer_items = stub.get_layers()

        publishable_ids = [layer.id for layer in layer_items
                           if layer.visible]

        # collect stored image instances
        instance_names = []
        for layer_item in layer_items:
            layer_meta_data = stub.read(layer_item, stored_items)

            # Skip layers without metadata.
            if layer_meta_data is None:
                continue

            # Skip containers.
            if "container" in layer_meta_data["id"]:
                continue

            # active might not be in legacy meta
            if layer_meta_data.get("active", True) and layer_item.visible:
                instance_names.append(layer_meta_data["subset"])

        if len(instance_names) == 0:
            variants = proj_settings.get(
                "photoshop", {}).get(
                "create", {}).get(
                "CreateImage", {}).get(
                "default_variants", [''])
            family = "image"

            variant = context.data.get("variant") or variants[0]

            subset_name = get_subset_name(
                family, variant, task_name, asset_doc,
                project_name, host_name
            )

            instance = context.create_instance(subset_name)
            instance.data["family"] = family
            instance.data["asset"] = asset_name
            instance.data["subset"] = subset_name
            instance.data["ids"] = publishable_ids
            instance.data["publish"] = True
            instance.data["creator_identifier"] = "auto_image"

            if auto_creator["mark_for_review"]:
                instance.data["creator_attributes"] = {"mark_for_review": True}
                instance.data["families"] = ["review"]

            self.log.info("auto image instance: {} ".format(instance.data))
