import os
import json
import collections
import platform

import click

from openpype.lib import register_event_callback
from openpype.modules import (
    OpenPypeModule,
    ITrayModule,
    IPluginPaths,
    ISettingsChangeListener
)
from openpype.settings import SaveWarningExc, get_project_settings
from openpype.settings.lib import get_system_settings
from openpype.lib import Logger

from openpype.pipeline import (
    get_current_project_name,
    get_current_asset_name,
    get_current_task_name
)

FTRACK_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_URL_NOT_SET = object()


class FtrackModule(
    OpenPypeModule,
    ITrayModule,
    IPluginPaths,
    ISettingsChangeListener
):
    name = "ftrack"

    def initialize(self, settings):
        ftrack_settings = settings[self.name]

        self.enabled = ftrack_settings["enabled"]
        self._settings_ftrack_url = ftrack_settings["ftrack_server"]
        self._ftrack_url = _URL_NOT_SET

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

        # Hooks when a file has been opened or saved
        register_event_callback("open", self.after_file_open)
        register_event_callback("after.save", self.after_file_save)

    def find_ftrack_task_entity(
        self, session, project_name, asset_name, task_name
    ):
        project_entity = session.query(
            "Project where full_name is \"{}\"".format(project_name)
        ).first()
        if not project_entity:
            self.log.warning(
                "Couldn't find project \"{}\" in Ftrack.".format(project_name)
            )
            return

        potential_task_entities = session.query((
            "TypedContext where parent.name is \"{}\" and project_id is \"{}\""
        ).format(asset_name, project_entity["id"])).all()
        filtered_entities = []
        for _entity in potential_task_entities:
            if (
                _entity.entity_type.lower() == "task"
                and _entity["name"] == task_name
            ):
                filtered_entities.append(_entity)

        if not filtered_entities:
            self.log.warning((
                "Couldn't find task \"{}\" under parent \"{}\" in Ftrack."
            ).format(task_name, asset_name))
            return

        if len(filtered_entities) > 1:
            self.log.warning((
                "Found more than one task \"{}\""
                " under parent \"{}\" in Ftrack."
            ).format(task_name, asset_name))
            return

        return filtered_entities[0]

    def after_file_open(self, event):
        project_name = get_current_project_name()
        project_settings = get_project_settings(project_name)

        # Do we want/need/can to update the status ? -------------------------------------------------------------------
        # --------------------------------------------------------------------------------------------------------------
        change_task_status = project_settings["ftrack"]["application_handlers"]["change_task_status"]
        if not change_task_status["enabled"]:
            self.log.debug("Status changes are disabled for project \"{}\"".format(project_name))
            return

        mapping = change_task_status["status_change_on_file_open"]
        if not mapping:
            # No rules registered, skip.
            return
        # --------------------------------------------------------------------------------------------------------------

        asset_name = get_current_asset_name()
        task_name = get_current_task_name()

        # Create session -----------------------------------------------------------------------------------------------
        # --------------------------------------------------------------------------------------------------------------
        try:
            session = self.create_ftrack_session()
        except Exception: # noqa
            self.log.warning("Couldn't create ftrack session.", exc_info=True)
            return
        # --------------------------------------------------------------------------------------------------------------

        # Find entity --------------------------------------------------------------------------------------------------
        # --------------------------------------------------------------------------------------------------------------
        entity = self.find_ftrack_task_entity(session, project_name, asset_name, task_name)
        if not entity:
            # No valid entity found, quit.
            return

        ent_path = "/".join([ent["name"] for ent in entity["link"]])
        actual_status = entity["status"]["name"].lower()
        # --------------------------------------------------------------------------------------------------------------

        # Find next status ---------------------------------------------------------------------------------------------
        # --------------------------------------------------------------------------------------------------------------
        if "__ignore__" in mapping:
            ignored_statuses = [status.lower() for status in mapping["__ignore__"]]
            if actual_status in ignored_statuses:
                # We can exit the status is flagged to be ignored
                return

            # Removing to avoid looping on it
            mapping.pop("__ignore__")

        next_status = None

        for to_status, from_statuses in mapping.items():
            from_statuses = [status.lower() for status in from_statuses]
            if "__any__" in from_statuses:
                next_status = to_status
                # Not breaking in case a better mapping is set after.
                continue

            if actual_status in from_statuses:
                next_status = to_status
                # We found a valid mapping (other that __any__) we stop looking.
                break

        if not next_status:
            # No valid next status found, skip.
            return
        # --------------------------------------------------------------------------------------------------------------

        # Change status on ftrack --------------------------------------------------------------------------------------
        # --------------------------------------------------------------------------------------------------------------
        try:
            query = "Status where name is \"{}\"".format(next_status)
            next_status_obj = session.query(query).one()

            entity["status"] = next_status_obj
            session.commit()
            self.log.debug("Changing status to \"{}\" <{}>".format(next_status, ent_path))
        except Exception:  # noqa
            session.rollback()
            msg = "Status \"{}\" in presets wasn't found on Ftrack entity type \"{}\"".format(next_status,
                                                                                              entity.entity_type)
            self.log.warning(msg)

    def after_file_save(self, event):
        print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
        print(json.dumps(event.to_data()))
        print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
        print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")

    def get_ftrack_url(self):
        """Resolved ftrack url.

        Resolving is trying to fill missing information in url and tried to
        connect to the server.

        Returns:
            Union[str, None]: Final variant of url or None if url could not be
                reached.
        """

        if self._ftrack_url is _URL_NOT_SET:
            self._ftrack_url = resolve_ftrack_url(
                self._settings_ftrack_url,
                logger=self.log
            )
        return self._ftrack_url

    ftrack_url = property(get_ftrack_url)

    @property
    def settings_ftrack_url(self):
        """Ftrack url from settings in a format as it is.

        Returns:
            str: Ftrack url from settings.
        """

        return self._settings_ftrack_url

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
        """Implementation for applications launch hooks."""

        return os.path.join(FTRACK_MODULE_DIR, "launch_hooks")

    def modify_application_launch_arguments(self, application, env):
        if not application.use_python_2:
            return

        self.log.info("Adding Ftrack Python 2 packages to PYTHONPATH.")

        # Prepare vendor dir path
        python_2_vendor = os.path.join(FTRACK_MODULE_DIR, "python2_vendor")

        # Add Python 2 modules
        python_paths = [
            # `python-ftrack-api`
            os.path.join(python_2_vendor, "ftrack-python-api", "source")
        ]

        # Load PYTHONPATH from current launch context
        python_path = env.get("PYTHONPATH")
        if python_path:
            python_paths.append(python_path)

        # Set new PYTHONPATH to launch context environments
        env["PYTHONPATH"] = os.pathsep.join(python_paths)

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
        from openpype.lib import ApplicationManager
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

        old_attr_values = old_value.get("attributes", {})
        new_attr_values = new_value.get("attributes", {})
        if not new_attr_values or old_attr_values == new_attr_values:
            # If no values or same as before, then just skip the update process
            return

        system_settings = get_system_settings()
        protect_attrs = system_settings["general"].get("project", {}).get("protect_anatomy_attributes", False)

        # If we just create the project on the server (prepare project) we want to send attributes to Ftrack
        bypass_protect_anatomy_attributes = new_value_metadata.get("bypass_protect_anatomy_attributes", False)
        if bypass_protect_anatomy_attributes:
            # Disable the protection
            protect_attrs = False

        if protect_attrs:
            self.log.warning("Anatomy attributes are protected/locked. "
                             "The only way to modify them is through the project settings on Ftrack.")
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


def _check_ftrack_url(url):
    import requests

    try:
        result = requests.get(url, allow_redirects=False)
    except requests.exceptions.RequestException:
        return False

    if (result.status_code != 200 or "FTRACK_VERSION" not in result.headers):
        return False
    return True


def resolve_ftrack_url(url, logger=None):
    """Checks if Ftrack server is responding."""

    if logger is None:
        logger = Logger.get_logger(__name__)

    url = url.strip("/ ")
    if not url:
        logger.error("Ftrack URL is not set!")
        return None

    if not url.startswith("http"):
        url = "https://" + url

    ftrack_url = None
    if url and _check_ftrack_url(url):
        ftrack_url = url

    if not ftrack_url and not url.endswith("ftrackapp.com"):
        ftrackapp_url = url + ".ftrackapp.com"
        if _check_ftrack_url(ftrackapp_url):
            ftrack_url = ftrackapp_url

    if not ftrack_url and _check_ftrack_url(url):
        ftrack_url = url

    if ftrack_url:
        logger.debug("Ftrack server \"{}\" is accessible.".format(ftrack_url))

    else:
        logger.error("Ftrack server \"{}\" is not accessible!".format(url))

    return ftrack_url


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
