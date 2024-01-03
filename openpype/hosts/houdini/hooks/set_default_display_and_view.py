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

        # 'OCIO_ACTIVE_DISPLAYS', 'OCIO_ACTIVE_VIEWS' are checked
        # as Admins can add them in Ayon env vars or Ayon tools.

        default_display = houdini_color_settings["default_display"]
        if default_display:
            # get 'OCIO_ACTIVE_DISPLAYS' value if exists.
            self._set_context_env("OCIO_ACTIVE_DISPLAYS", default_display)

        default_view = houdini_color_settings["default_view"]
        if default_view:
            # get 'OCIO_ACTIVE_VIEWS' value if exists.
            self._set_context_env("OCIO_ACTIVE_VIEWS", default_view)

    def _set_context_env(self, env_var, default_value):
        env_value = self.launch_context.env.get(env_var, "")
        new_value = ":".join(
                key for key in [default_value, env_value] if key
            )
        self.log.info(
                "Setting {} environment to: {}"
                .format(env_var, new_value)
            )
        self.launch_context.env[env_var] = new_value
