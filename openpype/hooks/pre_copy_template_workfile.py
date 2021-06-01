import os
import platform
import shutil
from openpype.lib import PreLaunchHook
from openpype.settings import (
    get_project_settings
)


class AddTemplateWorkfileToLaunchArgs(PreLaunchHook):
    """Add last workfile path to launch arguments.

    This is not possible to do for all applications the same way.
    """

    order = 0
    app_groups = ["blender", "photoshop", "tvpaint", "afftereffects"]

    def execute(self):
        if not self.data.get("start_last_workfile"):
            self.log.info("It is set to not start last workfile on start.")
            return

        last_workfile = self.data.get("last_workfile_path")
        if not last_workfile:
            self.log.warning("Last workfile was not collected.")
            return

        if not os.path.exists(last_workfile):
            self.log.info("Current context does not have any workfile yet.")
            from_template = self.workfile_path(last_workfile)
            if not from_template:
                return

        # Add path to workfile to arguments
        self.launch_context.launch_args.append(last_workfile)

    def workfile_path(self, last_workfile):

        project = self.data["project_name"]

        project_settings = get_project_settings(project)

        host_settings = project_settings[self.application.group.name]

        create_first_version = (
            host_settings
            ["workfile_builder"]
            ["create_first_version"]
        )

        if not create_first_version:
            return False

        template_path = (
            host_settings
            ["workfile_builder"]
            ["template_path"]
            [platform.system().lower()]
        )

        if template_path:
            if not os.path.exists(template_path):
                self.log.warning(
                    "Couldn't find workfile template file in {}".format(
                        template_path
                    )
                )
                return False

            self.log.info(
                f"Creating workfile from template: \"{template_path}\""
            )

            # Copy template workfile to new destinantion
            shutil.copy2(
                os.path.normpath(template_path),
                os.path.normpath(last_workfile)
            )

        self.log.info(f"Workfile to open: \"{last_workfile}\"")

        return True