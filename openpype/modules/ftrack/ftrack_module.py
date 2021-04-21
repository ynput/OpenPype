import os
import collections
from abc import ABCMeta, abstractmethod
import six
import openpype
from openpype.modules import (
    PypeModule,
    ITrayModule,
    IPluginPaths,
    ITimersManager,
    IUserModule,
    ILaunchHookPaths,
    ISettingsChangeListener
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
    ILaunchHookPaths,
    ISettingsChangeListener
):
    name = "ftrack"

    def initialize(self, settings):
        ftrack_settings = settings[self.name]

        self.enabled = ftrack_settings["enabled"]
        # Add http schema
        ftrack_url = ftrack_settings["ftrack_server"].strip("/ ")
        if ftrack_url:
            if "http" not in ftrack_url:
                ftrack_url = "https://" + ftrack_url

            # Check if "ftrack.app" is part os url
            if "ftrackapp.com" not in ftrack_url:
                ftrack_url = ftrack_url + ".ftrackapp.com"

        self.ftrack_url = ftrack_url

        current_dir = os.path.dirname(os.path.abspath(__file__))
        server_event_handlers_paths = [
            os.path.join(current_dir, "event_handlers_server")
        ]
        server_event_handlers_paths.extend(
            ftrack_settings["ftrack_events_path"]
        )
        user_event_handlers_paths = [
            os.path.join(current_dir, "event_handlers_user")
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

    def on_system_settings_save(self, *_args, **_kwargs):
        """Implementation of ISettingsChangeListener interface."""
        # Ignore
        return

    def on_project_settings_save(self, *_args, **_kwargs):
        """Implementation of ISettingsChangeListener interface."""
        # Ignore
        return

    def on_project_anatomy_save(
        self, old_value, new_value, changes, project_name
    ):
        """Implementation of ISettingsChangeListener interface."""
        if not project_name:
            return

        attributes_changes = changes.get("attributes")
        if not attributes_changes:
            return

        import ftrack_api
        from openpype.modules.ftrack.lib import avalon_sync

        session = self.create_ftrack_session()
        project_entity = session.query(
            "Project where full_name is \"{}\"".format(project_name)
        ).first()

        if not project_entity:
            self.log.warning((
                "Ftrack project with names \"{}\" was not found."
                " Skipping settings attributes change callback."
            ))
            return

        project_id = project_entity["id"]

        cust_attr, hier_attr = avalon_sync.get_pype_attr(session)
        cust_attr_by_key = {attr["key"]: attr for attr in cust_attr}
        hier_attrs_by_key = {attr["key"]: attr for attr in hier_attr}
        for key, value in attributes_changes.items():
            configuration = hier_attrs_by_key.get(key)
            if not configuration:
                configuration = cust_attr_by_key.get(key)
            if not configuration:
                continue

            # TODO add value validations
            # - value type and list items
            entity_key = collections.OrderedDict()
            entity_key["configuration_id"] = configuration["id"]
            entity_key["entity_id"] = project_id

            session.recorded_operations.push(
                ftrack_api.operation.UpdateEntityOperation(
                    "ContextCustomAttributeValue",
                    entity_key,
                    "value",
                    ftrack_api.symbol.NOT_SET,
                    value

                )
            )
        session.commit()

    def create_ftrack_session(self, **session_kwargs):
        import ftrack_api

        if "server_url" not in session_kwargs:
            session_kwargs["server_url"] = self.ftrack_url

        if "api_key" not in session_kwargs or "api_user" not in session_kwargs:
            from .lib import credentials
            cred = credentials.get_credentials()
            session_kwargs["api_user"] = cred.get("username")
            session_kwargs["api_key"] = cred.get("api_key")

        return ftrack_api.Session(**session_kwargs)

    def tray_init(self):
        from .tray import FtrackTrayWrapper
        self.tray_module = FtrackTrayWrapper(self)

    def tray_menu(self, parent_menu):
        return self.tray_module.tray_menu(parent_menu)

    def tray_start(self):
        return self.tray_module.validate()

    def tray_exit(self):
        return self.tray_module.stop_action_server()

    def set_credentials_to_env(self, username, api_key):
        os.environ["FTRACK_API_USER"] = username or ""
        os.environ["FTRACK_API_KEY"] = api_key or ""
