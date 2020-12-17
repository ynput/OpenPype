import os
import pyblish.api


class ValidateWorkfileProjectName(pyblish.api.ContextPlugin):
    """Validate project name stored in workfile metadata.

    It is not possible to publish from different project than is set in
    environment variable "AVALON_PROJECT".
    """

    label = "Validate Workfile Project Name"
    order = pyblish.api.ValidatorOrder

    def process(self, context):
        workfile_context = context.data["workfile_context"]
        workfile_project_name = workfile_context["project"]
        env_project_name = os.environ["AVALON_PROJECT"]
        if workfile_project_name == env_project_name:
            self.log.info((
                "Both workfile project and environment project are same. {}"
            ).format(env_project_name))
            return

        # Raise an error
        raise AssertionError((
            # Short message
            "Workfile from different Project ({})."
            # Description what's wrong
            " It is not possible to publish when TVPaint was launched in"
            "context of different project. Current context project is \"{}\"."
            " Launch TVPaint in context of project \"{}\" and then publish."
        ).format(
            workfile_project_name,
            env_project_name,
            workfile_project_name,
        ))
