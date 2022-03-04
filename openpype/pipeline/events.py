"""Events holding data about specific event."""
import os
import re
import inspect
import logging
import weakref
from uuid import uuid4
try:
    from weakref import WeakMethod
except Exception:
    from .python_2_comp import WeakMethod


class EventCallback(object):
    def __init__(self, topic, func_ref, func_name, func_path):
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
        self._func_ref = func_ref
        self._func_name = func_name
        self._func_path = func_path
        self._ref_valid = True
        self._enabled = True

        self._log = None

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
        """Calling this funcion will cause that callback will be removed."""
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
            sig = inspect.signature(callback)
            try:
                if len(sig.parameters) == 0:
                    callback()
                else:
                    callback(event)
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

    Can be used to anything because data are not much specific. Only required
    argument is topic which defines why event is happening and may be used for
    filtering.

    Arg:
        topic (str): Identifier of event.
        data (Any): Data specific for event. Dictionary is recommended.
    """
    _data = {}

    def __init__(self, topic, data=None, source=None):
        self._id = str(uuid4())
        self._topic = topic
        if data is None:
            data = {}
        self._data = data
        self._source = source

    def __getitem__(self, key):
        return self._data[key]

    def get(self, key, *args, **kwargs):
        return self._data.get(key, *args, **kwargs)

    @property
    def id(self):
        return self._id

    @property
    def source(self):
        return self._source

    @property
    def data(self):
        return self._data

    @property
    def topic(self):
        return self._topic

    def emit(self):
        """Emit event and trigger callbacks."""
        StoredCallbacks.emit_event(self)


class StoredCallbacks:
    _registered_callbacks = []

    @classmethod
    def add_callback(cls, topic, callback):
        # Convert callback into references
        #   - deleted functions won't cause crashes
        if inspect.ismethod(callback):
            ref = WeakMethod(callback)
        elif callable(callback):
            ref = weakref.ref(callback)
        else:
            # TODO add logs
            return

        function_name = callback.__name__
        function_path = os.path.abspath(inspect.getfile(callback))
        callback = EventCallback(topic, ref, function_name, function_path)
        cls._registered_callbacks.append(callback)
        return callback

    @classmethod
    def validate(cls):
        invalid_callbacks = []
        for callbacks in cls._registered_callbacks:
            for callback in tuple(callbacks):
                callback.validate_ref()
                if not callback.is_ref_valid:
                    invalid_callbacks.append(callback)

        for callback in invalid_callbacks:
            cls._registered_callbacks.remove(callback)

    @classmethod
    def emit_event(cls, event):
        invalid_callbacks = []
        for callback in cls._registered_callbacks:
            callback.process_event()
            if not callback.is_ref_valid:
                invalid_callbacks.append(callback)

        for callback in invalid_callbacks:
            cls._registered_callbacks.remove(callback)


def register_event_callback(topic, callback):
    """Add callback that will be executed on specific topic."""
    return StoredCallbacks.add_callback(topic, callback)


def emit_event(topic, data=None, source=None):
    """Emit event with topic and data.

    Returns:
        Event: Object of event that was emitted.
    """
    event = Event(topic, data, source)
    event.emit()
    return event
