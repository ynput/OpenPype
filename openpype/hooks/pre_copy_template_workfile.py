import os
import shutil
from openpype.settings import get_project_settings
from openpype.lib.applications import PreLaunchHook, LaunchTypes
from openpype.pipeline.workfile import (
    get_custom_workfile_template,
    get_custom_workfile_template_by_string_context
)


class CopyTemplateWorkfile(PreLaunchHook):
    """Copy workfile template.

    This is not possible to do for all applications the same way.

    Prelaunch hook works only if last workfile leads to not existing file.
        - That is possible only if it's first version.
    """

    # Before `AddLastWorkfileToLaunchArgs`
    order = 0
    app_groups = {"blender", "photoshop", "tvpaint", "aftereffects",
                  "wrap"}
    launch_types = {LaunchTypes.local}

    def execute(self):
        """Check if can copy template for context and do it if possible.

        First check if host for current project should create first workfile.
        Second check is if template is reachable and can be copied.

        Args:
            last_workfile(str): Path where template will be copied.

        Returns:
            None: This is a void method.
        """

        last_workfile = self.data.get("last_workfile_path")
        if not last_workfile:
            self.log.warning((
                "Last workfile was not collected."
                " Can't add it to launch arguments or determine if should"
                " copy template."
            ))
            return

        if os.path.exists(last_workfile):
            self.log.debug("Last workfile exists. Skipping {} process.".format(
                self.__class__.__name__
            ))
            return

        self.log.info("Last workfile does not exist.")

        project_name = self.data["project_name"]
        asset_name = self.data["asset_name"]
        task_name = self.data["task_name"]
        host_name = self.application.host_name

        project_settings = get_project_settings(project_name)

        project_doc = self.data.get("project_doc")
        asset_doc = self.data.get("asset_doc")
        anatomy = self.data.get("anatomy")
        if project_doc and asset_doc:
            self.log.debug("Started filtering of custom template paths.")
            template_path = get_custom_workfile_template(
                project_doc,
                asset_doc,
                task_name,
                host_name,
                anatomy,
                project_settings
            )

        else:
            self.log.warning((
                "Global data collection probably did not execute."
                " Using backup solution."
            ))
            template_path = get_custom_workfile_template_by_string_context(
                project_name,
                asset_name,
                task_name,
                host_name,
                anatomy,
                project_settings
            )

        if not template_path:
            self.log.info(
                "Registered custom templates didn't match current context."
            )
            return

        if not os.path.exists(template_path):
            self.log.warning(
                "Couldn't find workfile template file \"{}\"".format(
                    template_path
                )
            )
            return

        self.log.info(
            f"Creating workfile from template: \"{template_path}\""
        )

        # Copy template workfile to new destination
        shutil.copy2(
            os.path.normpath(template_path),
            os.path.normpath(last_workfile)
        )
