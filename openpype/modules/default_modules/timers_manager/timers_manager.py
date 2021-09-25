import os
import collections
from openpype.modules import OpenPypeModule
from openpype_interfaces import (
    ITimersManager,
    ITrayService,
    IIdleManager
)
from avalon.api import AvalonMongoDB


class ExampleTimersManagerConnector:
    """Timers manager can handle timers of multiple modules/addons.

    Module must have object under `timers_manager_connector` attribute with
    few methods. This is example class of the object that could be stored under
    module.

    Required methods are 'stop_timer' and 'start_timer'.

    # TODO pass asset document instead of `hierarchy`
    Example of `data` that are passed during changing timer:
    ```
    data = {
        "project_name": project_name,
        "task_name": task_name,
        "task_type": task_type,
        "hierarchy": hierarchy
    }
    ```
    """
    # Not needed at all
    def __init__(self, module):
        # Store timer manager module to be able call it's methods when needed
        self._timers_manager_module = None

        # Store module which want to use timers manager to have access
        self._module = module

    # Required
    def stop_timer(self):
        """Called by timers manager when module should stop timer."""
        self._module.stop_timer()

    # Required
    def start_timer(self, data):
        """Method called by timers manager when should start timer."""
        self._module.start_timer(data)

    # Optional
    def register_timers_manager(self, timer_manager_module):
        """Method called by timers manager where it's object is passed.

        This is moment when timers manager module can be store to be able
        call it's callbacks (e.g. timer started).
        """
        self._timers_manager_module = timer_manager_module

    # Custom implementation
    def timer_started(self, data):
        """This is example of possibility to trigger callbacks on manager."""
        if self._timers_manager_module is not None:
            self._timers_manager_module.timer_started(self._module.id, data)

    # Custom implementation
    def timer_stopped(self):
        if self._timers_manager_module is not None:
            self._timers_manager_module.timer_stopped(self._module.id)


class TimersManager(OpenPypeModule, ITrayService, IIdleManager):
    """ Handles about Timers.

    Should be able to start/stop all timers at once.

    To be able use this advantage module has to have attribute with name
    `timers_manager_connector` which has two methods 'stop_timer'
    and 'start_timer'. Optionally may have `register_timers_manager` where
    object of TimersManager module is passed to be able call it's callbacks.

    See `ExampleTimersManagerConnector`.
    """
    name = "timers_manager"
    label = "Timers Service"

    _required_methods = (
        "stop_timer",
        "start_timer"
    )

    def initialize(self, modules_settings):
        timers_settings = modules_settings[self.name]

        self.enabled = timers_settings["enabled"]

        auto_stop = timers_settings["auto_stop"]
        # When timer will stop if idle manager is running (minutes)
        full_time = int(timers_settings["full_time"] * 60)
        # How many minutes before the timer is stopped will popup the message
        message_time = int(timers_settings["message_time"] * 60)

        self.auto_stop = auto_stop
        self.time_show_message = full_time - message_time
        self.time_stop_timer = full_time

        self.is_running = False
        self.last_task = None

        # Tray attributes
        self.signal_handler = None
        self.widget_user_idle = None
        self.signal_handler = None

        self._connectors_by_module_id = {}
        self._modules_by_id = {}

    def tray_init(self):
        from .widget_user_idle import WidgetUserIdle, SignalHandler
        self.widget_user_idle = WidgetUserIdle(self)
        self.signal_handler = SignalHandler(self)

    def tray_start(self, *_a, **_kw):
        return

    def tray_exit(self):
        """Nothing special for TimersManager."""
        return

    def start_timer(self, project_name, asset_name, task_name, hierarchy):
        """
            Start timer for 'project_name', 'asset_name' and 'task_name'

            Called from REST api by hosts.

            Args:
                project_name (string)
                asset_name (string)
                task_name (string)
                hierarchy (string)
        """
        dbconn = AvalonMongoDB()
        dbconn.install()
        dbconn.Session["AVALON_PROJECT"] = project_name

        asset_doc = dbconn.find_one({
            "type": "asset", "name": asset_name
        })
        if not asset_doc:
            raise ValueError("Uknown asset {}".format(asset_name))

        task_type = ''
        try:
            task_type = asset_doc["data"]["tasks"][task_name]["type"]
        except KeyError:
            self.log.warning("Couldn't find task_type for {}".
                             format(task_name))

        hierarchy = hierarchy.split("\\")
        hierarchy.append(asset_name)

        data = {
            "project_name": project_name,
            "task_name": task_name,
            "task_type": task_type,
            "hierarchy": hierarchy
        }
        self.timer_started(None, data)

    def timer_started(self, source_id, data):
        for module_id, connector in self._connectors_by_module_id.items():
            if module_id == source_id:
                continue

            try:
                connector.start_timer(data)
            except Exception:
                self.log.info(
                    "Failed to start timer on connector {}".format(
                        str(connector)
                    )
                )

        self.last_task = data
        self.is_running = True

    def timer_stopped(self, source_id):
        for module_id, connector in self._connectors_by_module_id.items():
            if module_id == source_id:
                continue

            try:
                connector.stop_timer()
            except Exception:
                self.log.info(
                    "Failed to stop timer on connector {}".format(
                        str(connector)
                    )
                )

    def restart_timers(self):
        if self.last_task is not None:
            self.timer_started(None, self.last_task)

    def stop_timers(self):
        if self.is_running is False:
            return

        self.widget_user_idle.bool_not_stopped = False
        self.widget_user_idle.refresh_context()
        self.is_running = False

        self.timer_stopped(None)

    def connect_with_modules(self, enabled_modules):
        for module in enabled_modules:
            connector = getattr(module, "timers_manager_connector", None)
            if connector is None:
                continue

            missing_methods = set()
            for method_name in self._required_methods:
                if not hasattr(connector, method_name):
                    missing_methods.add(method_name)

            if missing_methods:
                joined = ", ".join(
                    ['"{}"'.format(name for name in missing_methods)]
                )
                self.log.info((
                    "Module \"{}\" has missing required methods {}."
                ).format(module.name, joined))
                continue

            self._connectors_by_module_id[module.id] = connector
            self._modules_by_id[module.id] = module

            # Optional method
            if hasattr(connector, "register_timers_manager"):
                try:
                    connector.register_timers_manager(self)
                except Exception:
                    self.log.info((
                        "Failed to register timers manager"
                        " for connector of module \"{}\"."
                    ).format(module.name))

    def callbacks_by_idle_time(self):
        """Implementation of IIdleManager interface."""
        # Time when message is shown
        if not self.auto_stop:
            return {}

        callbacks = collections.defaultdict(list)
        callbacks[self.time_show_message].append(lambda: self.time_callback(0))

        # Times when idle is between show widget and stop timers
        show_to_stop_range = range(
            self.time_show_message - 1, self.time_stop_timer
        )
        for num in show_to_stop_range:
            callbacks[num].append(lambda: self.time_callback(1))

        # Times when widget is already shown and user restart idle
        shown_and_moved_range = range(
            self.time_stop_timer - self.time_show_message
        )
        for num in shown_and_moved_range:
            callbacks[num].append(lambda: self.time_callback(1))

        # Time when timers are stopped
        callbacks[self.time_stop_timer].append(lambda: self.time_callback(2))

        return callbacks

    def time_callback(self, int_def):
        if not self.signal_handler:
            return

        if int_def == 0:
            self.signal_handler.signal_show_message.emit()
        elif int_def == 1:
            self.signal_handler.signal_change_label.emit()
        elif int_def == 2:
            self.signal_handler.signal_stop_timers.emit()

    def change_label(self):
        if self.is_running is False:
            return

        if (
            not self.idle_manager
            or self.widget_user_idle.bool_is_showed is False
        ):
            return

        if self.idle_manager.idle_time > self.time_show_message:
            value = self.time_stop_timer - self.idle_manager.idle_time
        else:
            value = 1 + (
                self.time_stop_timer -
                self.time_show_message -
                self.idle_manager.idle_time
            )
        self.widget_user_idle.change_count_widget(value)

    def show_message(self):
        if self.is_running is False:
            return
        if self.widget_user_idle.bool_is_showed is False:
            self.widget_user_idle.show()

    # Webserver module implementation
    def webserver_initialization(self, server_manager):
        """Add routes for timers to be able start/stop with rest api."""
        if self.tray_initialized:
            from .rest_api import TimersManagerModuleRestApi
            self.rest_api_obj = TimersManagerModuleRestApi(
                self, server_manager
            )

    def change_timer_from_host(self, project_name, asset_name, task_name):
        """Prepared method for calling change timers on REST api"""
        webserver_url = os.environ.get("OPENPYPE_WEBSERVER_URL")
        if not webserver_url:
            self.log.warning("Couldn't find webserver url")
            return

        rest_api_url = "{}/timers_manager/start_timer".format(webserver_url)
        try:
            import requests
        except Exception:
            self.log.warning("Couldn't start timer")
            return
        data = {
            "project_name": project_name,
            "asset_name": asset_name,
            "task_name": task_name
        }

        requests.post(rest_api_url, json=data)
