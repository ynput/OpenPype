"""
Provides:
    context -> projectName (str)
    context -> asset (str)
    context -> task (str)
"""

import pyblish.api
from openpype.pipeline import legacy_io


class CollectCurrentContext(pyblish.api.ContextPlugin):
    """Collect project context into publish context data.

    Plugin does not override any value if is already set.
    """

    order = pyblish.api.CollectorOrder - 0.5
    label = "Collect Current context"

    def process(self, context):
        # Make sure 'legacy_io' is intalled
        legacy_io.install()

        # Check if values are already set
        project_name = context.data.get("projectName")
        asset_name = context.data.get("asset")
        task_name = context.data.get("task")
        if not project_name:
            project_name = legacy_io.current_project()
            context.data["projectName"] = project_name

        if not asset_name:
            asset_name = legacy_io.Session.get("AVALON_ASSET")
            context.data["asset"] = asset_name

        if not task_name:
            task_name = legacy_io.Session.get("AVALON_TASK")
            context.data["task"] = task_name

        # QUESTION should we be explicit with keys? (the same on instances)
        #   - 'asset' -> 'assetName'
        #   - 'task' -> 'taskName'

        self.log.info((
            "Collected project context\nProject: {}\nAsset: {}\nTask: {}"
        ).format(project_name, asset_name, task_name))
