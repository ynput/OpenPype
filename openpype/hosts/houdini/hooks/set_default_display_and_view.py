from openpype.lib.applications import PreLaunchHook, LaunchTypes
from openpype.settings import get_project_settings


class SetDefaultDislayView(PreLaunchHook):
    """Set default view and default display for houdini host that use OpenColorIO.

    Houdini's defaultDisplay and defaultView are set by
    setting 'OCIO_ACTIVE_DISPLAYS' and 'OCIO_ACTIVE_VIEWS'
    environment variables respectively.

    More info: https://www.sidefx.com/docs/houdini/io/ocio.html#set-up
    """

    app_groups = {"houdini"}
    launch_types = {LaunchTypes.local}

    def execute(self):

        OCIO = self.launch_context.env.get("OCIO")

        # This is a cheap way to skip this hook if either
        # global color management or houdini color management was disabled.
        if not OCIO:
            return

        project_settings = get_project_settings(
            project_name=self.data["project_name"]
        )

        houdini_color_Settings = \
            project_settings["houdini"]["imageio"]["workfile"]

        if not houdini_color_Settings["enabled"]:
            self.log.info(
                "Houdini's workefile color settings are disabled."
            )
            return

        default_display = houdini_color_Settings["default_display"]
        default_view = houdini_color_Settings["default_view"]

        self.log.info(
            "Setting OCIO_ACTIVE_DISPLAYS environment to : {}"
            .format(default_display)
        )
        self.launch_context.env["OCIO_ACTIVE_DISPLAYS"] = default_display

        self.log.info(
            "Setting OCIO_ACTIVE_VIEWS environment to config path: {}"
            .format(default_view)
        )
        self.launch_context.env["OCIO_ACTIVE_VIEWS"] = default_view
