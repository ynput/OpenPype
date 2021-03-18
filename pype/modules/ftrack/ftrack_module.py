import os
from abc import ABCMeta, abstractmethod
import six
import pype
from pype.modules import (
    PypeModule,
    ITrayModule,
    IPluginPaths,
    ITimersManager,
    IUserModule,
    ILaunchHookPaths
)

FTRACK_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


@six.add_metaclass(ABCMeta)
class IFtrackEventHandlerPaths:
    """Other modules interface to return paths to ftrack event handlers.

    Expected output is dictionary with "server" and "user" keys.
    """
    @abstractmethod
    def get_event_handler_paths(self):
        pass


class FtrackModule(
    PypeModule,
    ITrayModule,
    IPluginPaths,
    ITimersManager,
    IUserModule,
    ILaunchHookPaths
):
    name = "ftrack"

    def initialize(self, settings):
        ftrack_settings = settings[self.name]

        self.enabled = ftrack_settings["enabled"]
        self.ftrack_url = ftrack_settings["ftrack_server"]

        current_dir = os.path.dirname(os.path.abspath(__file__))
        server_event_handlers_paths = [
            os.path.join(current_dir, "events")
        ]
        server_event_handlers_paths.extend(
            ftrack_settings["ftrack_events_path"]
        )
        user_event_handlers_paths = [
            os.path.join(current_dir, "actions")
        ]
        user_event_handlers_paths.extend(
            ftrack_settings["ftrack_actions_path"]
        )
        # Prepare attribute
        self.server_event_handlers_paths = server_event_handlers_paths
        self.user_event_handlers_paths = user_event_handlers_paths
        self.tray_module = None

    def get_global_environments(self):
        """Ftrack's global environments."""
        return {
            "FTRACK_SERVER": self.ftrack_url
        }

    def get_plugin_paths(self):
        """Ftrack plugin paths."""
        return {
            "publish": [os.path.join(FTRACK_MODULE_DIR, "plugins", "publish")]
        }

    def get_launch_hook_paths(self):
        """Implementation of `ILaunchHookPaths`."""
        return os.path.join(FTRACK_MODULE_DIR, "launch_hooks")

    def connect_with_modules(self, enabled_modules):
        for module in enabled_modules:
            if not isinstance(module, IFtrackEventHandlerPaths):
                continue
            paths_by_type = module.get_event_handler_paths() or {}
            for key, value in paths_by_type.items():
                if not value:
                    continue

                if key not in ("server", "user"):
                    self.log.warning(
                        "Unknown event handlers key \"{}\" skipping.".format(
                            key
                        )
                    )
                    continue

                if not isinstance(value, (list, tuple, set)):
                    value = [value]

                if key == "server":
                    self.server_event_handlers_paths.extend(value)
                elif key == "user":
                    self.user_event_handlers_paths.extend(value)

    def start_timer(self, data):
        """Implementation of ITimersManager interface."""
        if self.tray_module:
            self.tray_module.start_timer_manager(data)

    def stop_timer(self):
        """Implementation of ITimersManager interface."""
        if self.tray_module:
            self.tray_module.stop_timer_manager()

    def on_pype_user_change(self, username):
        """Implementation of IUserModule interface."""
        if self.tray_module:
            self.tray_module.changed_user()

    def tray_init(self):
        from .tray import FtrackTrayWrapper
        self.tray_module = FtrackTrayWrapper(self)

    def tray_menu(self, parent_menu):
        return self.tray_module.tray_menu(parent_menu)

    def tray_start(self):
        return self.tray_module.validate()

    def tray_exit(self):
        return self.tray_module.stop_action_server()
