from openpype.lib.applications import PreLaunchHook, LaunchTypes


class SetDefaultDisplayView(PreLaunchHook):
    """Set default view and default display for houdini via OpenColorIO.

    Houdini's defaultDisplay and defaultView are set by
    setting 'OCIO_ACTIVE_DISPLAYS' and 'OCIO_ACTIVE_VIEWS'
    environment variables respectively.

    More info: https://www.sidefx.com/docs/houdini/io/ocio.html#set-up
    """

    app_groups = {"houdini"}
    launch_types = {LaunchTypes.local}

    def execute(self):

        OCIO = self.launch_context.env.get("OCIO")

        # This is a cheap way to skip this hook if either global color
        # management or houdini color management was disabled because the
        # OCIO var would be set by the global OCIOEnvHook
        if not OCIO:
            return

        houdini_color_settings = \
            self.data["project_settings"]["houdini"]["imageio"]["workfile"]

        if not houdini_color_settings["enabled"]:
            self.log.info(
                "Houdini workfile color management is disabled."
            )
            return

        # This is a way to get values specified by admins if they already
        # added 'OCIO_ACTIVE_DISPLAYS', 'OCIO_ACTIVE_VIEWS' manually
        # using Ayon global env vars or Ayon app env vars
        # or Ayon houdini tool
        OCIO_ACTIVE_DISPLAYS = self.launch_context.env.get(
            "OCIO_ACTIVE_DISPLAYS", ""
        )
        OCIO_ACTIVE_VIEWS = self.launch_context.env.get(
            "OCIO_ACTIVE_VIEWS", ""
        )

        # default_display and default_view
        default_display = houdini_color_settings["default_display"]
        default_display = ":".join([default_display, OCIO_ACTIVE_DISPLAYS])

        default_view = houdini_color_settings["default_view"]
        default_view = ":".join([default_view, OCIO_ACTIVE_VIEWS])

        self.log.info(
            "Setting OCIO_ACTIVE_DISPLAYS environment to: {}"
            .format(default_display)
        )
        self.launch_context.env["OCIO_ACTIVE_DISPLAYS"] = default_display

        self.log.info(
            "Setting OCIO_ACTIVE_VIEWS environment to: {}"
            .format(default_view)
        )
        self.launch_context.env["OCIO_ACTIVE_VIEWS"] = default_view
