from abc import ABCMeta, abstractmethod
import six
from .. import PypeModule, ITrayService, IIdleManager


@six.add_metaclass(ABCMeta)
class ITimersManager:
    timer_manager_module = None

    @abstractmethod
    def stop_timer(self):
        pass

    @abstractmethod
    def start_timer(self, data):
        pass

    def timer_started(self, data):
        if not self.timer_manager_module:
            return

        self.timer_manager_module.timer_started(self.id, data)

    def timer_stopped(self):
        if not self.timer_manager_module:
            return

        self.timer_manager_module.timer_stopped(self.id)


class TimersManager(PypeModule, ITrayService, IIdleManager):
    """ Handles about Timers.

    Should be able to start/stop all timers at once.
    If IdleManager is imported then is able to handle about stop timers
        when user idles for a long time (set in presets).
    """
    name = "timers_manager"
    label = "Timers Service"

    def initialize(self, modules_settings):
        timers_settings = modules_settings[self.name]

        self.enabled = timers_settings["enabled"]
        # When timer will stop if idle manager is running (minutes)
        full_time = int(timers_settings["full_time"] * 60)
        # How many minutes before the timer is stopped will popup the message
        message_time = int(timers_settings["message_time"] * 60)

        self.time_show_message = full_time - message_time
        self.time_stop_timer = full_time

        self.is_running = False
        self.last_task = None

        # Tray attributes
        self.signal_handler = None
        self.widget_user_idle = None
        self.signal_handler = None

        self.modules = []

    def tray_init(self):
        from .widget_user_idle import WidgetUserIdle, SignalHandler
        self.widget_user_idle = WidgetUserIdle(self)
        self.signal_handler = SignalHandler(self)

    def tray_start(self, *_a, **_kw):
        return

    def tray_exit(self):
        """Nothing special for TimersManager."""
        return

    def timer_started(self, source_id, data):
        for module in self.modules:
            if module.id != source_id:
                module.start_timer(data)

        self.last_task = data
        self.is_running = True

    def timer_stopped(self, source_id):
        for module in self.modules:
            if module.id != source_id:
                module.stop_timer()

    def restart_timers(self):
        if self.last_task is not None:
            self.timer_started(None, self.last_task)

    def stop_timers(self):
        if self.is_running is False:
            return

        self.widget_user_idle.bool_not_stopped = False
        self.widget_user_idle.refresh_context()
        self.is_running = False

        for module in self.modules:
            module.stop_timer()

    def connect_with_modules(self, enabled_modules):
        for module in enabled_modules:
            if not isinstance(module, ITimersManager):
                continue
            module.timer_manager_module = self
            self.modules.append(module)

    def callbacks_by_idle_time(self):
        """Implementation of IIdleManager interface."""
        # Time when message is shown
        callbacks = {
            self.time_show_message: lambda: self.time_callback(0)
        }

        # Times when idle is between show widget and stop timers
        show_to_stop_range = range(
            self.time_show_message - 1, self.time_stop_timer
        )
        for num in show_to_stop_range:
            callbacks[num] = lambda: self.time_callback(1)

        # Times when widget is already shown and user restart idle
        shown_and_moved_range = range(
            self.time_stop_timer - self.time_show_message
        )
        for num in shown_and_moved_range:
            callbacks[num] = lambda: self.time_callback(1)

        # Time when timers are stopped
        callbacks[self.time_stop_timer] = lambda: self.time_callback(2)

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
