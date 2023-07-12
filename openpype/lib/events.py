"""Events holding data about specific event."""
import os
import re
import copy
import inspect
import logging
import weakref
from uuid import uuid4

from .python_2_comp import WeakMethod
from .python_module_tools import is_func_signature_supported


class MissingEventSystem(Exception):
    pass


class EventCallback(object):
    """Callback registered to a topic.

    The callback function is registered to a topic. Topic is a string which
    may contain '*' that will be handled as "any characters".

    # Examples:
    - "workfile.save"   Callback will be triggered if the event topic is
                        exactly "workfile.save" .
    - "workfile.*"      Callback will be triggered an event topic starts with
                        "workfile." so "workfile.save" and "workfile.open"
                        will trigger the callback.
    - "*"               Callback will listen to all events.

    Callback can be function or method. In both cases it should expect one
    or none arguments. When 1 argument is expected then the processed 'Event'
    object is passed in.

    The registered callbacks don't keep function in memory so it is not
    possible to store lambda function as callback.

    Args:
        topic(str): Topic which will be listened.
        func(func): Callback to a topic.

    Raises:
        TypeError: When passed function is not a callable object.
    """

    def __init__(self, topic, func):
        self._log = None
        self._topic = topic
        # Replace '*' with any character regex and escape rest of text
        #   - when callback is registered for '*' topic it will receive all
        #       events
        #   - it is possible to register to a partial topis 'my.event.*'
        #       - it will receive all matching event topics
        #           e.g. 'my.event.start' and 'my.event.end'
        topic_regex_str = "^{}$".format(
            ".+".join(
                re.escape(part)
                for part in topic.split("*")
            )
        )
        topic_regex = re.compile(topic_regex_str)
        self._topic_regex = topic_regex

        # Convert callback into references
        #   - deleted functions won't cause crashes
        if inspect.ismethod(func):
            func_ref = WeakMethod(func)
        elif callable(func):
            func_ref = weakref.ref(func)
        else:
            raise TypeError((
                "Registered callback is not callable. \"{}\""
            ).format(str(func)))

        # Collect function name and path to file for logging
        func_name = func.__name__
        func_path = os.path.abspath(inspect.getfile(func))

        # Get expected arguments from function spec
        # - positional arguments are always preferred
        expect_args = is_func_signature_supported(func, "fake")
        expect_kwargs = is_func_signature_supported(func, event="fake")

        self._func_ref = func_ref
        self._func_name = func_name
        self._func_path = func_path
        self._expect_args = expect_args
        self._expect_kwargs = expect_kwargs
        self._ref_valid = func_ref is not None
        self._enabled = True

    def __repr__(self):
        return "< {} - {} > {}".format(
            self.__class__.__name__, self._func_name, self._func_path
        )

    @property
    def log(self):
        if self._log is None:
            self._log = logging.getLogger(self.__class__.__name__)
        return self._log

    @property
    def is_ref_valid(self):
        return self._ref_valid

    def validate_ref(self):
        if not self._ref_valid:
            return

        callback = self._func_ref()
        if not callback:
            self._ref_valid = False

    @property
    def enabled(self):
        """Is callback enabled."""
        return self._enabled

    def set_enabled(self, enabled):
        """Change if callback is enabled."""
        self._enabled = enabled

    def deregister(self):
        """Calling this function will cause that callback will be removed."""
        # Fake reference
        self._ref_valid = False

    def topic_matches(self, topic):
        """Check if event topic matches callback's topic."""
        return self._topic_regex.match(topic)

    def process_event(self, event):
        """Process event.

        Args:
            event(Event): Event that was triggered.
        """

        # Skip if callback is not enabled or has invalid reference
        if not self._ref_valid or not self._enabled:
            return

        # Get reference
        callback = self._func_ref()
        # Check if reference is valid or callback's topic matches the event
        if not callback:
            # Change state if is invalid so the callback is removed
            self._ref_valid = False

        elif self.topic_matches(event.topic):
            # Try execute callback
            try:
                if self._expect_args:
                    callback(event)

                elif self._expect_kwargs:
                    callback(event=event)

                else:
                    callback()

            except Exception:
                self.log.warning(
                    "Failed to execute event callback {}".format(
                        str(repr(self))
                    ),
                    exc_info=True
                )


# Inherit from 'object' for Python 2 hosts
class Event(object):
    """Base event object.

    Can be used for any event because is not specific. Only required argument
    is topic which defines why event is happening and may be used for
    filtering.

    Arg:
        topic (str): Identifier of event.
        data (Any): Data specific for event. Dictionary is recommended.
        source (str): Identifier of source.
        event_system (EventSystem): Event system in which can be event
            triggered.
    """

    _data = {}

    def __init__(self, topic, data=None, source=None, event_system=None):
        self._id = str(uuid4())
        self._topic = topic
        if data is None:
            data = {}
        self._data = data
        self._source = source
        self._event_system = event_system

    def __getitem__(self, key):
        return self._data[key]

    def get(self, key, *args, **kwargs):
        return self._data.get(key, *args, **kwargs)

    @property
    def id(self):
        return self._id

    @property
    def source(self):
        """Event's source used for triggering callbacks.

        Returns:
            Union[str, None]: Source string or None. Source is optional.
        """

        return self._source

    @property
    def data(self):
        return self._data

    @property
    def topic(self):
        """Event's topic used for triggering callbacks.

        Returns:
            str: Topic string.
        """

        return self._topic

    def emit(self):
        """Emit event and trigger callbacks."""
        if self._event_system is None:
            raise MissingEventSystem(
                "Can't emit event {}. Does not have set event system.".format(
                    str(repr(self))
                )
            )
        self._event_system.emit_event(self)

    def to_data(self):
        """Convert Event object to data.

        Returns:
            Dict[str, Any]: Event data.
        """

        return {
            "id": self.id,
            "topic": self.topic,
            "source": self.source,
            "data": copy.deepcopy(self.data)
        }

    @classmethod
    def from_data(cls, event_data, event_system=None):
        """Create event from data.

        Args:
            event_data (Dict[str, Any]): Event data with defined keys. Can be
                created using 'to_data' method.
            event_system (EventSystem): System to which the event belongs.

        Returns:
            Event: Event with attributes from passed data.
        """

        obj = cls(
            event_data["topic"],
            event_data["data"],
            event_data["source"],
            event_system
        )
        obj._id = event_data["id"]
        return obj


class EventSystem(object):
    """Encapsulate event handling into an object.

    System wraps registered callbacks and triggered events into single object
    so it is possible to create mutltiple independent systems that have their
    topics and callbacks.


    """

    def __init__(self):
        self._registered_callbacks = []

    def add_callback(self, topic, callback):
        """Register callback in event system.

        Args:
            topic (str): Topic for EventCallback.
            callback (Callable): Function or method that will be called
                when topic is triggered.

        Returns:
            EventCallback: Created callback object which can be used to
                stop listening.
        """

        callback = EventCallback(topic, callback)
        self._registered_callbacks.append(callback)
        return callback

    def create_event(self, topic, data, source):
        """Create new event which is bound to event system.

        Args:
            topic (str): Event topic.
            data (dict): Data related to event.
            source (str): Source of event.

        Returns:
            Event: Object of event.
        """

        return Event(topic, data, source, self)

    def emit(self, topic, data, source):
        """Create event based on passed data and emit it.

        This is easiest way how to trigger event in an event system.

        Args:
            topic (str): Event topic.
            data (dict): Data related to event.
            source (str): Source of event.

        Returns:
            Event: Created and emitted event.
        """

        event = self.create_event(topic, data, source)
        event.emit()
        return event

    def emit_event(self, event):
        """Emit event object.

        Args:
            event (Event): Prepared event with topic and data.
        """

        invalid_callbacks = []
        for callback in self._registered_callbacks:
            callback.process_event(event)
            if not callback.is_ref_valid:
                invalid_callbacks.append(callback)

        for callback in invalid_callbacks:
            self._registered_callbacks.remove(callback)


class GlobalEventSystem:
    """Event system living in global scope of process.

    This is primarily used in host implementation to trigger events
    related to DCC changes or changes of context in the host implementation.
    """

    _global_event_system = None

    @classmethod
    def get_global_event_system(cls):
        if cls._global_event_system is None:
            cls._global_event_system = EventSystem()
        return cls._global_event_system

    @classmethod
    def add_callback(cls, topic, callback):
        event_system = cls.get_global_event_system()
        return event_system.add_callback(topic, callback)

    @classmethod
    def emit(cls, topic, data, source):
        event_system = cls.get_global_event_system()
        return event_system.emit(topic, data, source)


def register_event_callback(topic, callback):
    """Add callback that will be executed on specific topic.

    Args:
        topic(str): Topic on which will callback be triggered.
        callback(function): Callback that will be triggered when a topic
            is triggered. Callback should expect none or 1 argument where
            `Event` object is passed.

    Returns:
        EventCallback: Object wrapping the callback. It can be used to
            enable/disable listening to a topic or remove the callback from
            the topic completely.
    """

    return GlobalEventSystem.add_callback(topic, callback)


def emit_event(topic, data=None, source=None):
    """Emit event with topic and data.

    Arg:
        topic(str): Event's topic.
        data(dict): Event's additional data. Optional.
        source(str): Who emitted the topic. Optional.

    Returns:
        Event: Object of event that was emitted.
    """

    return GlobalEventSystem.emit(topic, data, source)
