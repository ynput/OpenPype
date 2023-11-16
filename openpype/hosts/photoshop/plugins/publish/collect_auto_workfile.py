import os
import pyblish.api

from openpype.client import get_asset_name_identifier
from openpype.hosts.photoshop import api as photoshop
from openpype.pipeline.create import get_subset_name


class CollectAutoWorkfile(pyblish.api.ContextPlugin):
    """Collect current script for publish."""

    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect Workfile"
    hosts = ["photoshop"]

    targets = ["automated"]

    def process(self, context):
        family = "workfile"
        file_path = context.data["currentFile"]
        _, ext = os.path.splitext(file_path)
        staging_dir = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)
        workfile_representation = {
            "name": ext[1:],
            "ext": ext[1:],
            "files": base_name,
            "stagingDir": staging_dir,
        }

        for instance in context:
            if instance.data["family"] == family:
                self.log.debug("Workfile instance found, won't create new")
                instance.data.update({
                    "label": base_name,
                    "name": base_name,
                    "representations": [],
                })

                # creating representation
                _, ext = os.path.splitext(file_path)
                instance.data["representations"].append(
                    workfile_representation)

                return

        stub = photoshop.stub()
        stored_items = stub.get_layers_metadata()
        for item in stored_items:
            if item.get("creator_identifier") == family:
                if not item.get("active"):
                    self.log.debug("Workfile instance disabled")
                    return

        project_name = context.data["projectName"]
        proj_settings = context.data["project_settings"]
        auto_creator = proj_settings.get(
            "photoshop", {}).get(
            "create", {}).get(
            "WorkfileCreator", {})

        if not auto_creator or not auto_creator["enabled"]:
            self.log.debug("Workfile creator disabled, won't create new")
            return

        # context.data["variant"] might come only from collect_batch_data
        variant = (context.data.get("variant") or
                   auto_creator["default_variant"])

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

        # Create instance
        instance = context.create_instance(subset_name)
        instance.data.update({
            "subset": subset_name,
            "label": base_name,
            "name": base_name,
            "family": family,
            "families": [],
            "representations": [],
            "asset": asset_name
        })

        # creating representation
        instance.data["representations"].append(workfile_representation)

        self.log.debug("auto workfile review created:{}".format(instance.data))
