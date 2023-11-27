"""Create instances based on CreateContext.

"""
import os
import pyblish.api

from openpype import AYON_SERVER_ENABLED
from openpype.host import IPublishHost
from openpype.pipeline import legacy_io, registered_host
from openpype.pipeline.create import CreateContext


class CollectFromCreateContext(pyblish.api.ContextPlugin):
    """Collect instances and data from CreateContext from new publishing."""

    label = "Collect From Create Context"
    order = pyblish.api.CollectorOrder - 0.5

    def process(self, context):
        create_context = context.data.get("create_context")
        if not create_context:
            host = registered_host()
            if isinstance(host, IPublishHost):
                create_context = CreateContext(host)

        if not create_context:
            return

        thumbnail_paths_by_instance_id = (
            create_context.thumbnail_paths_by_instance_id
        )
        context.data["thumbnailSource"] = (
            thumbnail_paths_by_instance_id.get(None)
        )

        project_name = create_context.get_current_project_name()
        if project_name:
            context.data["projectName"] = project_name

        for created_instance in create_context.instances:
            instance_data = created_instance.data_to_store()
            if AYON_SERVER_ENABLED:
                instance_data["asset"] = instance_data.pop("folderPath")
            if instance_data["active"]:
                thumbnail_path = thumbnail_paths_by_instance_id.get(
                    created_instance.id
                )
                self.create_instance(
                    context,
                    instance_data,
                    created_instance.transient_data,
                    thumbnail_path
                )

        # Update global data to context
        context.data.update(create_context.context_data_to_store())
        context.data["newPublishing"] = True
        # Update context data
        asset_name = create_context.get_current_asset_name()
        task_name = create_context.get_current_task_name()
        for key, value in (
            ("AVALON_PROJECT", project_name),
            ("AVALON_ASSET", asset_name),
            ("AVALON_TASK", task_name)
        ):
            legacy_io.Session[key] = value
            os.environ[key] = value

    def create_instance(
        self,
        context,
        in_data,
        transient_data,
        thumbnail_path
    ):
        subset = in_data["subset"]
        # If instance data already contain families then use it
        instance_families = in_data.get("families") or []

        instance = context.create_instance(subset)
        instance.data.update({
            "subset": subset,
            "asset": in_data["asset"],
            "task": in_data["task"],
            "label": in_data.get("label") or subset,
            "name": subset,
            "family": in_data["family"],
            "families": instance_families,
            "representations": [],
            "thumbnailSource": thumbnail_path
        })
        for key, value in in_data.items():
            if key not in instance.data:
                instance.data[key] = value

        instance.data["transientData"] = transient_data

        self.log.debug("collected instance: {}".format(instance.data))
        self.log.debug("parsing data: {}".format(in_data))
