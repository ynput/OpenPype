import os
import json
import collections
import platform

import click

from openpype.modules import OpenPypeModule
from openpype_interfaces import (
    ITrayModule,
    IPluginPaths,
    ILaunchHookPaths,
    ISettingsChangeListener
)
from openpype.settings import SaveWarningExc

FTRACK_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


class FtrackModule(
    OpenPypeModule,
    ITrayModule,
    IPluginPaths,
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
        low_platform = platform.system().lower()

        # Server event handler paths
        server_event_handlers_paths = [
            os.path.join(current_dir, "event_handlers_server")
        ]
        settings_server_paths = ftrack_settings["ftrack_events_path"]
        if isinstance(settings_server_paths, dict):
            settings_server_paths = settings_server_paths[low_platform]
        server_event_handlers_paths.extend(settings_server_paths)

        # User event handler paths
        user_event_handlers_paths = [
            os.path.join(current_dir, "event_handlers_user")
        ]
        settings_action_paths = ftrack_settings["ftrack_actions_path"]
        if isinstance(settings_action_paths, dict):
            settings_action_paths = settings_action_paths[low_platform]
        user_event_handlers_paths.extend(settings_action_paths)

        # Prepare attribute
        self.server_event_handlers_paths = server_event_handlers_paths
        self.user_event_handlers_paths = user_event_handlers_paths
        self.tray_module = None

        # TimersManager connection
        self.timers_manager_connector = None
        self._timers_manager_module = None

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
            if not hasattr(module, "get_ftrack_event_handler_paths"):
                continue

            try:
                paths_by_type = module.get_ftrack_event_handler_paths()
            except Exception:
                continue

            if not isinstance(paths_by_type, dict):
                continue

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

    def on_system_settings_save(
        self, old_value, new_value, changes, new_value_metadata
    ):
        """Implementation of ISettingsChangeListener interface."""
        if not self.ftrack_url:
            raise SaveWarningExc((
                "Ftrack URL is not set."
                " Can't propagate changes to Ftrack server."
            ))

        ftrack_changes = changes.get("modules", {}).get("ftrack", {})
        url_change_msg = None
        if "ftrack_server" in ftrack_changes:
            url_change_msg = (
                "Ftrack URL was changed."
                " This change may need to restart OpenPype to take affect."
            )

        try:
            session = self.create_ftrack_session()
        except Exception:
            self.log.warning("Couldn't create ftrack session.", exc_info=True)

            if url_change_msg:
                raise SaveWarningExc(url_change_msg)

            raise SaveWarningExc((
                "Saving of attributes to ftrack wasn't successful,"
                " try running Create/Update Avalon Attributes in ftrack."
            ))

        from .lib import (
            get_openpype_attr,
            CUST_ATTR_APPLICATIONS,
            CUST_ATTR_TOOLS,
            app_definitions_from_app_manager,
            tool_definitions_from_app_manager
        )
        from openpype.api import ApplicationManager
        query_keys = [
            "id",
            "key",
            "config"
        ]
        custom_attributes = get_openpype_attr(
            session,
            split_hierarchical=False,
            query_keys=query_keys
        )
        app_attribute = None
        tool_attribute = None
        for custom_attribute in custom_attributes:
            key = custom_attribute["key"]
            if key == CUST_ATTR_APPLICATIONS:
                app_attribute = custom_attribute
            elif key == CUST_ATTR_TOOLS:
                tool_attribute = custom_attribute

        app_manager = ApplicationManager(new_value_metadata)
        missing_attributes = []
        if not app_attribute:
            missing_attributes.append(CUST_ATTR_APPLICATIONS)
        else:
            config = json.loads(app_attribute["config"])
            new_data = app_definitions_from_app_manager(app_manager)
            prepared_data = []
            for item in new_data:
                for key, label in item.items():
                    prepared_data.append({
                        "menu": label,
                        "value": key
                    })

            config["data"] = json.dumps(prepared_data)
            app_attribute["config"] = json.dumps(config)

        if not tool_attribute:
            missing_attributes.append(CUST_ATTR_TOOLS)
        else:
            config = json.loads(tool_attribute["config"])
            new_data = tool_definitions_from_app_manager(app_manager)
            prepared_data = []
            for item in new_data:
                for key, label in item.items():
                    prepared_data.append({
                        "menu": label,
                        "value": key
                    })
            config["data"] = json.dumps(prepared_data)
            tool_attribute["config"] = json.dumps(config)

        session.commit()

        if missing_attributes:
            raise SaveWarningExc((
                "Couldn't find custom attribute/s ({}) to update."
                " Try running Create/Update Avalon Attributes in ftrack."
            ).format(", ".join(missing_attributes)))

        if url_change_msg:
            raise SaveWarningExc(url_change_msg)

    def on_project_settings_save(self, *_args, **_kwargs):
        """Implementation of ISettingsChangeListener interface."""
        # Ignore
        return

    def on_project_anatomy_save(
        self, old_value, new_value, changes, project_name, new_value_metadata
    ):
        """Implementation of ISettingsChangeListener interface."""
        if not project_name:
            return

        new_attr_values = new_value.get("attributes")
        if not new_attr_values:
            return

        import ftrack_api
        from openpype_modules.ftrack.lib import (
            get_openpype_attr,
            default_custom_attributes_definition,
            CUST_ATTR_TOOLS,
            CUST_ATTR_APPLICATIONS,
            CUST_ATTR_INTENT
        )

        try:
            session = self.create_ftrack_session()
        except Exception:
            self.log.warning("Couldn't create ftrack session.", exc_info=True)
            raise SaveWarningExc((
                "Saving of attributes to ftrack wasn't successful,"
                " try running Create/Update Avalon Attributes in ftrack."
            ))

        project_entity = session.query(
            "Project where full_name is \"{}\"".format(project_name)
        ).first()

        if not project_entity:
            msg = (
                "Ftrack project with name \"{}\" was not found in Ftrack."
                " Can't push attribute changes."
            ).format(project_name)
            self.log.warning(msg)
            raise SaveWarningExc(msg)

        project_id = project_entity["id"]

        ca_defs = default_custom_attributes_definition()
        hierarchical_attrs = ca_defs.get("is_hierarchical") or {}
        project_attrs = ca_defs.get("show") or {}
        ca_keys = (
            set(hierarchical_attrs.keys())
            | set(project_attrs.keys())
            | {CUST_ATTR_TOOLS, CUST_ATTR_APPLICATIONS, CUST_ATTR_INTENT}
        )

        cust_attr, hier_attr = get_openpype_attr(session)
        cust_attr_by_key = {attr["key"]: attr for attr in cust_attr}
        hier_attrs_by_key = {attr["key"]: attr for attr in hier_attr}

        failed = {}
        missing = {}
        for key, value in new_attr_values.items():
            if key not in ca_keys:
                continue

            configuration = hier_attrs_by_key.get(key)
            if not configuration:
                configuration = cust_attr_by_key.get(key)
            if not configuration:
                self.log.warning(
                    "Custom attribute \"{}\" was not found.".format(key)
                )
                missing[key] = value
                continue

            # TODO add add permissions check
            # TODO add value validations
            # - value type and list items
            entity_key = collections.OrderedDict([
                ("configuration_id", configuration["id"]),
                ("entity_id", project_id)
            ])

            session.recorded_operations.push(
                ftrack_api.operation.UpdateEntityOperation(
                    "ContextCustomAttributeValue",
                    entity_key,
                    "value",
                    ftrack_api.symbol.NOT_SET,
                    value
                )
            )
            try:
                session.commit()
                self.log.debug(
                    "Changed project custom attribute \"{}\" to \"{}\"".format(
                        key, value
                    )
                )
            except Exception:
                self.log.warning(
                    "Failed to set \"{}\" to \"{}\"".format(key, value),
                    exc_info=True
                )
                session.rollback()
                failed[key] = value

        if not failed and not missing:
            return

        error_msg = (
            "Values were not updated on Ftrack which may cause issues."
            " try running Create/Update Avalon Attributes in ftrack "
            " and resave project settings."
        )
        if missing:
            error_msg += "\nMissing Custom attributes on Ftrack: {}.".format(
                ", ".join([
                    '"{}"'.format(key)
                    for key in missing.keys()
                ])
            )
        if failed:
            joined_failed = ", ".join([
                '"{}": "{}"'.format(key, value)
                for key, value in failed.items()
            ])
            error_msg += "\nFailed to set: {}".format(joined_failed)
        raise SaveWarningExc(error_msg)

    def create_ftrack_session(self, **session_kwargs):
        import ftrack_api

        if "server_url" not in session_kwargs:
            session_kwargs["server_url"] = self.ftrack_url

        api_key = session_kwargs.get("api_key")
        api_user = session_kwargs.get("api_user")
        # First look into environments
        # - both OpenPype tray and ftrack event server should have set them
        # - ftrack event server may crash when credentials are tried to load
        #   from keyring
        if not api_key or not api_user:
            api_key = os.environ.get("FTRACK_API_KEY")
            api_user = os.environ.get("FTRACK_API_USER")

        if not api_key or not api_user:
            from .lib import credentials
            cred = credentials.get_credentials()
            api_user = cred.get("username")
            api_key = cred.get("api_key")

        session_kwargs["api_user"] = api_user
        session_kwargs["api_key"] = api_key
        return ftrack_api.Session(**session_kwargs)

    def tray_init(self):
        from .tray import FtrackTrayWrapper

        self.tray_module = FtrackTrayWrapper(self)
        # Module is it's own connector to TimersManager
        self.timers_manager_connector = self

    def tray_menu(self, parent_menu):
        return self.tray_module.tray_menu(parent_menu)

    def tray_start(self):
        return self.tray_module.validate()

    def tray_exit(self):
        self.tray_module.tray_exit()

    def set_credentials_to_env(self, username, api_key):
        os.environ["FTRACK_API_USER"] = username or ""
        os.environ["FTRACK_API_KEY"] = api_key or ""

    # --- TimersManager connection methods ---
    def start_timer(self, data):
        if self.tray_module:
            self.tray_module.start_timer_manager(data)

    def stop_timer(self):
        if self.tray_module:
            self.tray_module.stop_timer_manager()

    def register_timers_manager(self, timer_manager_module):
        self._timers_manager_module = timer_manager_module

    def timer_started(self, data):
        if self._timers_manager_module is not None:
            self._timers_manager_module.timer_started(self.id, data)

    def timer_stopped(self):
        if self._timers_manager_module is not None:
            self._timers_manager_module.timer_stopped(self.id)

    def get_task_time(self, project_name, asset_name, task_name):
        session = self.create_ftrack_session()
        query = (
            'Task where name is "{}"'
            ' and parent.name is "{}"'
            ' and project.full_name is "{}"'
        ).format(task_name, asset_name, project_name)
        task_entity = session.query(query).first()
        if not task_entity:
            return 0
        hours_logged = (task_entity["time_logged"] / 60) / 60
        return hours_logged

    def get_credentials(self):
        # type: () -> tuple
        """Get local Ftrack credentials."""
        from .lib import credentials

        cred = credentials.get_credentials(self.ftrack_url)
        return cred.get("username"), cred.get("api_key")

    def cli(self, click_group):
        click_group.add_command(cli_main)


@click.group(FtrackModule.name, help="Ftrack module related commands.")
def cli_main():
    pass


@cli_main.command()
@click.option("-d", "--debug", is_flag=True, help="Print debug messages")
@click.option("--ftrack-url", envvar="FTRACK_SERVER",
              help="Ftrack server url")
@click.option("--ftrack-user", envvar="FTRACK_API_USER",
              help="Ftrack api user")
@click.option("--ftrack-api-key", envvar="FTRACK_API_KEY",
              help="Ftrack api key")
@click.option("--legacy", is_flag=True,
              help="run event server without mongo storing")
@click.option("--clockify-api-key", envvar="CLOCKIFY_API_KEY",
              help="Clockify API key.")
@click.option("--clockify-workspace", envvar="CLOCKIFY_WORKSPACE",
              help="Clockify workspace")
def eventserver(
    debug,
    ftrack_url,
    ftrack_user,
    ftrack_api_key,
    legacy,
    clockify_api_key,
    clockify_workspace
):
    """Launch ftrack event server.

    This should be ideally used by system service (such us systemd or upstart
    on linux and window service).
    """
    if debug:
        os.environ["OPENPYPE_DEBUG"] = "3"

    from .ftrack_server.event_server_cli import run_event_server

    return run_event_server(
        ftrack_url,
        ftrack_user,
        ftrack_api_key,
        legacy,
        clockify_api_key,
        clockify_workspace
    )
