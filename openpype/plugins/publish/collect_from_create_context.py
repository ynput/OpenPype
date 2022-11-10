"""Create instances based on CreateContext.

"""
import os
import pyblish.api

from openpype.pipeline import legacy_io


class CollectFromCreateContext(pyblish.api.ContextPlugin):
    """Collect instances and data from CreateContext from new publishing."""

    label = "Collect From Create Context"
    order = pyblish.api.CollectorOrder - 0.5

    def process(self, context):
        create_context = context.data.pop("create_context", None)
        # Skip if create context is not available
        if not create_context:
            return

        thumbnail_paths_by_instance_id = (
            create_context.thumbnail_paths_by_instance_id
        )
        context.data["thumbnailSource"] = (
            thumbnail_paths_by_instance_id.get(None)
        )

        project_name = create_context.project_name
        if project_name:
            context.data["projectName"] = project_name

        for created_instance in create_context.instances:
            instance_data = created_instance.data_to_store()
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
        for key in ("AVALON_PROJECT", "AVALON_ASSET", "AVALON_TASK"):
            value = create_context.dbcon.Session.get(key)
            if value is not None:
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

        self.log.info("collected instance: {}".format(instance.data))
        self.log.info("parsing data: {}".format(in_data))
