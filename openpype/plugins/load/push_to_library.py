import os

from openpype import PACKAGE_DIR, AYON_SERVER_ENABLED
from openpype.lib import get_openpype_execute_args, run_detached_process
from openpype.pipeline import load
from openpype.pipeline.load import LoadError


class PushToLibraryProject(load.SubsetLoaderPlugin):
    """Export selected versions to folder structure from Template"""

    is_multiple_contexts_compatible = True

    representations = ["*"]
    families = ["*"]

    label = "Push to Library project"
    order = 35
    icon = "send"
    color = "#d8d8d8"

    def load(self, contexts, name=None, namespace=None, options=None):
        filtered_contexts = [
            context
            for context in contexts
            if context.get("project") and context.get("version")
        ]
        if not filtered_contexts:
            raise LoadError("Nothing to push for your selection")

        if len(filtered_contexts) > 1:
            raise LoadError("Please select only one item")

        context = tuple(filtered_contexts)[0]

        if AYON_SERVER_ENABLED:
            push_tool_script_path = os.path.join(
                PACKAGE_DIR,
                "tools",
                "ayon_push_to_project",
                "main.py"
            )
        else:
            push_tool_script_path = os.path.join(
                PACKAGE_DIR,
                "tools",
                "push_to_project",
                "app.py"
            )

        project_doc = context["project"]
        version_doc = context["version"]
        project_name = project_doc["name"]
        version_id = str(version_doc["_id"])

        args = get_openpype_execute_args(
            "run",
            push_tool_script_path,
            "--project", project_name,
            "--version", version_id
        )
        run_detached_process(args)
