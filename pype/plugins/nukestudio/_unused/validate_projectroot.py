from pyblish import api


class RepairProjectRoot(api.Action):

    label = "Repair"
    icon = "wrench"
    on = "failed"

    def process(self, context, plugin):
        import os

        project_root = os.path.join(
            os.path.dirname(context.data["currentFile"])
        )

        context.data["activeProject"].setProjectRoot(project_root)


class ValidateProjectRoot(api.ContextPlugin):
    """Validate the project root to the workspace directory."""

    order = api.ValidatorOrder
    label = "Project Root"
    hosts = ["nukestudio"]
    actions = [RepairProjectRoot]

    def process(self, context):
        import os

        workspace = os.path.join(
            os.path.dirname(context.data["currentFile"])
        )
        project_root = context.data["activeProject"].projectRoot()

        failure_message = (
            'The project root needs to be "{0}", its currently: "{1}"'
            ).format(workspace, project_root)

        assert project_root == workspace, failure_message
