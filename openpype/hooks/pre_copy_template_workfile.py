import os
import shutil
from openpype.lib import (
    PreLaunchHook,
    get_custom_workfile_template_by_context,
    get_custom_workfile_template_by_string_context
)
from openpype.settings import get_project_settings


class CopyTemplateWorkfile(PreLaunchHook):
    """Copy workfile template.

    This is not possible to do for all applications the same way.

    Prelaunch hook works only if last workfile leads to not existing file.
        - That is possible only if it's first version.
    """

    # Before `AddLastWorkfileToLaunchArgs`
    order = 0
    app_groups = ["blender", "photoshop", "tvpaint", "aftereffects"]

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

        project_settings = get_project_settings(project_name)
        host_settings = project_settings[self.application.host_name]

        workfile_builder_settings = host_settings.get("workfile_builder")
        if not workfile_builder_settings:
            # TODO remove warning when deprecated
            self.log.warning((
                "Seems like old version of settings is used."
                " Can't access custom templates in host \"{}\"."
            ).format(self.application.full_label))
            return

        if not workfile_builder_settings["create_first_version"]:
            self.log.info((
                "Project \"{}\" has turned off to create first workfile for"
                " application \"{}\""
            ).format(project_name, self.application.full_label))
            return

        # Backwards compatibility
        template_profiles = workfile_builder_settings.get("custom_templates")
        if not template_profiles:
            self.log.info(
                "Custom templates are not filled. Skipping template copy."
            )
            return

        project_doc = self.data.get("project_doc")
        asset_doc = self.data.get("asset_doc")
        anatomy = self.data.get("anatomy")
        if project_doc and asset_doc:
            self.log.debug("Started filtering of custom template paths.")
            template_path = get_custom_workfile_template_by_context(
                template_profiles, project_doc, asset_doc, task_name, anatomy
            )

        else:
            self.log.warning((
                "Global data collection probably did not execute."
                " Using backup solution."
            ))
            dbcon = self.data.get("dbcon")
            template_path = get_custom_workfile_template_by_string_context(
                template_profiles, project_name, asset_name, task_name,
                dbcon, anatomy
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
