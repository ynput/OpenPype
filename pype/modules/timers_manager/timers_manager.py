from Qt import QtCore
from .widget_user_idle import WidgetUserIdle
from pype.api import Logger, config


class Singleton(type):
    """ Signleton implementation
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(
                Singleton, cls
            ).__call__(*args, **kwargs)
        return cls._instances[cls]


class TimersManager(metaclass=Singleton):
    """ Handles about Timers.

    Should be able to start/stop all timers at once.
    If IdleManager is imported then is able to handle about stop timers
        when user idles for a long time (set in presets).
    """
    modules = []
    is_running = False
    last_task = None

    def __init__(self, tray_widget, main_widget):
        self.log = Logger().get_logger(self.__class__.__name__)
        self.tray_widget = tray_widget
        self.main_widget = main_widget
        self.widget_user_idle = WidgetUserIdle(self)

    def set_signal_times(self):
        try:
            timer_info = (
                config.get_presets()
                .get('services')
                .get('timers_manager')
                .get('timer')
            )
            full_time = int(float(timer_info['full_time'])*60)
            message_time = int(float(timer_info['message_time'])*60)
            self.time_show_message = full_time - message_time
            self.time_stop_timer = full_time
            return True
        except Exception:
            self.log.warning('Was not able to load presets for TimersManager')
            return False

    def add_module(self, module):
        """ Adds module to context

        Module must have implemented methods:
            - ``start_timer_manager(data)``
            - ``stop_timer_manager()``
        """
        self.modules.append(module)

    def start_timers(self, data):
        '''
        :param data: basic information needed to start any timer
        :type data: dict
        ..note::
            Dictionary "data" should contain:
            - project_name(str) - Name of Project
            - hierarchy(list/tuple) - list of parents(except project)
            - task_type(str)
            - task_name(str)

        Example:
            - to run timers for task in
                'C001_BackToPast/assets/characters/villian/Lookdev BG'
            - input data should contain:
            .. code-block:: Python
                data = {
                    'project_name': 'C001_BackToPast',
                    'hierarchy': ['assets', 'characters', 'villian'],
                    'task_type': 'lookdev',
                    'task_name': 'Lookdev BG'
                }
        '''
        if len(data['hierarchy']) < 1:
            self.log.error((
                'Not allowed action in Pype!!'
                ' Timer has been launched on task which is child of Project.'
            ))
            return

        self.last_task = data

        for module in self.modules:
            module.start_timer_manager(data)
        self.is_running = True

    def restart_timers(self):
        if self.last_task is not None:
            self.start_timers(self.last_task)

    def stop_timers(self):
        if self.is_running is False:
            return
        self.widget_user_idle.bool_not_stopped = False
        self.widget_user_idle.refresh_context()
        for module in self.modules:
            module.stop_timer_manager()
        self.is_running = False

    def process_modules(self, modules):
        """ Gives ability to connect with imported modules from TrayManager.

        :param modules: All imported modules from TrayManager
        :type modules: dict
        """
        self.s_handler = SignalHandler(self)

        if 'IdleManager' in modules:
            if self.set_signal_times() is True:
                self.register_to_idle_manager(modules['IdleManager'])

    def register_to_idle_manager(self, man_obj):
        self.idle_man = man_obj
        # Times when idle is between show widget and stop timers
        show_to_stop_range = range(
            self.time_show_message-1, self.time_stop_timer
        )
        for num in show_to_stop_range:
            self.idle_man.add_time_signal(
                num,
                self.s_handler.signal_change_label
            )
        # Times when widget is already shown and user restart idle
        shown_and_moved_range = range(
            self.time_stop_timer - self.time_show_message
        )
        for num in shown_and_moved_range:
            self.idle_man.add_time_signal(
                num,
                self.s_handler.signal_change_label
            )
        # Time when message is shown
        self.idle_man.add_time_signal(
            self.time_show_message,
            self.s_handler.signal_show_message
        )
        # Time when timers are stopped
        self.idle_man.add_time_signal(
            self.time_stop_timer,
            self.s_handler.signal_stop_timers
        )

    def change_label(self):
        if self.is_running is False:
            return
        if self.widget_user_idle.bool_is_showed is False:
            return
        if not hasattr(self, 'idle_man'):
            return

        if self.idle_man.idle_time > self.time_show_message:
            value = self.time_stop_timer - self.idle_man.idle_time
        else:
            value = 1 + (
                self.time_stop_timer -
                self.time_show_message -
                self.idle_man.idle_time
            )
        self.widget_user_idle.change_count_widget(value)

    def show_message(self):
        if self.is_running is False:
            return
        if self.widget_user_idle.bool_is_showed is False:
            self.widget_user_idle.show()


class SignalHandler(QtCore.QObject):
    signal_show_message = QtCore.Signal()
    signal_change_label = QtCore.Signal()
    signal_stop_timers = QtCore.Signal()
    def __init__(self, cls):
        super().__init__()
        self.signal_show_message.connect(cls.show_message)
        self.signal_change_label.connect(cls.change_label)
        self.signal_stop_timers.connect(cls.stop_timers)
