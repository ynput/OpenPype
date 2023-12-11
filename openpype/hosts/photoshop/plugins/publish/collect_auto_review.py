"""
Requires:
    None

Provides:
    instance     -> family ("review")
"""
import pyblish.api

from openpype.client import get_asset_name_identifier
from openpype.hosts.photoshop import api as photoshop
from openpype.pipeline.create import get_subset_name


class CollectAutoReview(pyblish.api.ContextPlugin):
    """Create review instance in non artist based workflow.

    Called only if PS is triggered in Webpublisher or in tests.
    """

    label = "Collect Auto Review"
    hosts = ["photoshop"]
    order = pyblish.api.CollectorOrder + 0.2
    targets = ["automated"]

    publish = True

    def process(self, context):
        family = "review"
        has_review = False
        for instance in context:
            if instance.data["family"] == family:
                self.log.debug("Review instance found, won't create new")
                has_review = True

            creator_attributes = instance.data.get("creator_attributes", {})
            if (creator_attributes.get("mark_for_review") and
                    "review" not in instance.data["families"]):
                instance.data["families"].append("review")

        if has_review:
            return

        stub = photoshop.stub()
        stored_items = stub.get_layers_metadata()
        for item in stored_items:
            if item.get("creator_identifier") == family:
                if not item.get("active"):
                    self.log.debug("Review instance disabled")
                    return

        auto_creator = context.data["project_settings"].get(
            "photoshop", {}).get(
            "create", {}).get(
            "ReviewCreator", {})

        if not auto_creator or not auto_creator["enabled"]:
            self.log.debug("Review creator disabled, won't create new")
            return

        variant = (context.data.get("variant") or
                   auto_creator["default_variant"])

        project_name = context.data["projectName"]
        proj_settings = context.data["project_settings"]
        task_name = context.data["task"]
        host_name = context.data["hostName"]
        asset_doc = context.data["assetEntity"]

        asset_name = get_asset_name_identifier(asset_doc)

        subset_name = get_subset_name(
            family,
            variant,
            task_name,
            asset_doc,
            project_name,
            host_name=host_name,
            project_settings=proj_settings
        )

        instance = context.create_instance(subset_name)
        instance.data.update({
            "subset": subset_name,
            "label": subset_name,
            "name": subset_name,
            "family": family,
            "families": [],
            "representations": [],
            "asset": asset_name,
            "publish": self.publish
        })

        self.log.debug("auto review created::{}".format(instance.data))
