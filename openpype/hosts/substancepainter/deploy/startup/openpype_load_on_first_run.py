"""Ease the OpenPype on-boarding process by loading the plug-in on first run"""

OPENPYPE_PLUGIN_NAME = "openpype_plugin"


def start_plugin():
    try:
        # This isn't exposed in the official API so we keep it in a try-except
        from painter_plugins_ui import (
            get_settings,
            LAUNCH_AT_START_KEY,
            ON_STATE,
            PLUGINS_MENU,
            plugin_manager
        )

        # The `painter_plugins_ui` plug-in itself is also a startup plug-in
        # we need to take into account that it could run either earlier or
        # later than this startup script, we check whether its menu initialized
        is_before_plugins_menu = PLUGINS_MENU is None

        settings = get_settings(OPENPYPE_PLUGIN_NAME)
        if settings.value(LAUNCH_AT_START_KEY, None) is None:
            print("Initializing OpenPype plug-in on first run...")
            if is_before_plugins_menu:
                print("- running before 'painter_plugins_ui'")
                # Delay the launch to the painter_plugins_ui initialization
                settings.setValue(LAUNCH_AT_START_KEY, ON_STATE)
            else:
                # Launch now
                print("- running after 'painter_plugins_ui'")
                plugin_manager(OPENPYPE_PLUGIN_NAME)(True)

                # Set the checked state in the menu to avoid confusion
                action = next(action for action in PLUGINS_MENU._menu.actions()
                              if action.text() == OPENPYPE_PLUGIN_NAME)
                if action is not None:
                    action.blockSignals(True)
                    action.setChecked(True)
                    action.blockSignals(False)

    except Exception as exc:
        print(exc)
