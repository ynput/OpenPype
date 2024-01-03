"""Events holding data about specific event."""
import os
import re
import copy
import inspect
import collections
import logging
import weakref
from uuid import uuid4

from .python_2_comp import WeakMethod
from .python_module_tools import is_func_signature_supported


class MissingEventSystem(Exception):
    pass


def _get_func_ref(func):
    if inspect.ismethod(func):
        return WeakMethod(func)
    return weakref.ref(func)


def _get_func_info(func):
    path = "<unknown path>"
    if func is None:
        return "<unknown>", path

    if hasattr(func, "__name__"):
        name = func.__name__
    else:
        name = str(func)

    # Get path to file and fallback to '<unknown path>' if fails
    # NOTE This was added because of 'partial' functions which is handled,
    #   but who knows what else can cause this to fail?
    try:
        path = os.path.abspath(inspect.getfile(func))
    except TypeError:
        pass

    return name, path


class weakref_partial:
    """Partial function with weak reference to the wrapped function.

    Can be used as 'functools.partial' but it will store weak reference to
        function. That means that the function must be reference counted
        to avoid garbage collecting the function itself.

        When the referenced functions is garbage collected then calling the
        weakref partial (no matter the args/kwargs passed) will do nothing.
        It will fail silently, returning `None`. The `is_valid()` method can
        be used to detect whether the reference is still valid.

    Is useful for object methods. In that case the callback is
        deregistered when object is destroyed.

    Warnings:
        Values passed as *args and **kwargs are stored strongly in memory.
            That may "keep alive" objects that should be already destroyed.
            It is recommended to pass only immutable objects like 'str',
            'bool', 'int' etc.

    Args:
        func (Callable): Function to wrap.
        *args: Arguments passed to the wrapped function.
        **kwargs: Keyword arguments passed to the wrapped function.
    """

    def __init__(self, func, *args, **kwargs):
        self._func_ref = _get_func_ref(func)
        self._args = args
        self._kwargs = kwargs

    def __call__(self, *args, **kwargs):
        func = self._func_ref()
        if func is None:
            return

        new_args = tuple(list(self._args) + list(args))
        new_kwargs = dict(self._kwargs)
        new_kwargs.update(kwargs)
        return func(*new_args, **new_kwargs)

    def get_func(self):
        """Get wrapped function.

        Returns:
            Union[Callable, None]: Wrapped function or None if it was
                destroyed.
        """

        return self._func_ref()

    def is_valid(self):
        """Check if wrapped function is still valid.

        Returns:
            bool: Is wrapped function still valid.
        """

        return self._func_ref() is not None

    def validate_signature(self, *args, **kwargs):
        """Validate if passed arguments are supported by wrapped function.

        Returns:
            bool: Are passed arguments supported by wrapped function.
        """

        func = self._func_ref()
        if func is None:
            return False

        new_args = tuple(list(self._args) + list(args))
        new_kwargs = dict(self._kwargs)
        new_kwargs.update(kwargs)
        return is_func_signature_supported(
            func, *new_args, **new_kwargs
        )


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

    The callbacks are validated against their reference counter, that is
        achieved using 'weakref' module. That means that the callback must
        be stored in memory somewhere. e.g. lambda functions are not
        supported as valid callback.

    You can use 'weakref_partial' functions. In that case is partial object
        stored in the callback object and reference counter is checked for
        the wrapped function.

    Args:
        topic (str): Topic which will be listened.
        func (Callable): Callback to a topic.
        order (Union[int, None]): Order of callback. Lower number means higher
            priority.

    Raises:
        TypeError: When passed function is not a callable object.
    """

    def __init__(self, topic, func, order):
        if not callable(func):
            raise TypeError((
                "Registered callback is not callable. \"{}\""
            ).format(str(func)))

        self._validate_order(order)

        self._log = None
        self._topic = topic
        self._order = order
        self._enabled = True
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

        # Callback function prep
        if isinstance(func, weakref_partial):
            partial_func = func
            (name, path) = _get_func_info(func.get_func())
            func_ref = None
            expect_args = partial_func.validate_signature("fake")
            expect_kwargs = partial_func.validate_signature(event="fake")

        else:
            partial_func = None
            (name, path) = _get_func_info(func)
            # Convert callback into references
            #   - deleted functions won't cause crashes
            func_ref = _get_func_ref(func)

            # Get expected arguments from function spec
            # - positional arguments are always preferred
            expect_args = is_func_signature_supported(func, "fake")
            expect_kwargs = is_func_signature_supported(func, event="fake")

        self._func_ref = func_ref
        self._partial_func = partial_func
        self._ref_is_valid = True
        self._expect_args = expect_args
        self._expect_kwargs = expect_kwargs

        self._name = name
        self._path = path

    def __repr__(self):
        return "< {} - {} > {}".format(
            self.__class__.__name__, self._name, self._path
        )

    @property
    def log(self):
        if self._log is None:
            self._log = logging.getLogger(self.__class__.__name__)
        return self._log

    @property
    def is_ref_valid(self):
        """

        Returns:
            bool: Is reference to callback valid.
        """

        self._validate_ref()
        return self._ref_is_valid

    def validate_ref(self):
        """Validate if reference to callback is valid.

        Deprecated:
            Reference is always live checkd with 'is_ref_valid'.
        """

        # Trigger validate by getting 'is_valid'
        _ = self.is_ref_valid

    @property
    def enabled(self):
        """Is callback enabled.

        Returns:
            bool: Is callback enabled.
        """

        return self._enabled

    def set_enabled(self, enabled):
        """Change if callback is enabled.

        Args:
            enabled (bool): Change enabled state of the callback.
        """

        self._enabled = enabled

    def deregister(self):
        """Calling this function will cause that callback will be removed."""

        self._ref_is_valid = False
        self._partial_func = None
        self._func_ref = None

    def get_order(self):
        """Get callback order.

        Returns:
            Union[int, None]: Callback order.
        """

        return self._order

    def set_order(self, order):
        """Change callback order.

        Args:
            order (Union[int, None]): Order of callback. Lower number means
                higher priority.
        """

        self._validate_order(order)
        self._order = order

    order = property(get_order, set_order)

    def topic_matches(self, topic):
        """Check if event topic matches callback's topic.

        Args:
            topic (str): Topic name.

        Returns:
            bool: Topic matches callback's topic.
        """

        return self._topic_regex.match(topic)

    def process_event(self, event):
        """Process event.

        Args:
            event(Event): Event that was triggered.
        """

        # Skip if callback is not enabled
        if not self._enabled:
            return

        # Get reference and skip if is not available
        callback = self._get_callback()
        if callback is None:
            return

        if not self.topic_matches(event.topic):
            return

        # Try to execute callback
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

    def _validate_order(self, order):
        if isinstance(order, int):
            return

        raise TypeError(
            "Expected type 'int' got '{}'.".format(str(type(order)))
        )

    def _get_callback(self):
        if self._partial_func is not None:
            return self._partial_func

        if self._func_ref is not None:
            return self._func_ref()
        return None

    def _validate_ref(self):
        if self._ref_is_valid is False:
            return

        if self._func_ref is not None:
            self._ref_is_valid = self._func_ref() is not None

        elif self._partial_func is not None:
            self._ref_is_valid = self._partial_func.is_valid()

        else:
            self._ref_is_valid = False

        if not self._ref_is_valid:
            self._func_ref = None
            self._partial_func = None


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

    System wraps registered callbacks and triggered events into single object,
    so it is possible to create multiple independent systems that have their
    topics and callbacks.

    Callbacks are stored by order of their registration, but it is possible to
    manually define order of callbacks using 'order' argument within
    'add_callback'.
    """

    default_order = 100

    def __init__(self):
        self._registered_callbacks = []

    def add_callback(self, topic, callback, order=None):
        """Register callback in event system.

        Args:
            topic (str): Topic for EventCallback.
            callback (Union[Callable, weakref_partial]): Function or method
                that will be called when topic is triggered.
            order (Optional[int]): Order of callback. Lower number means
                higher priority.

        Returns:
            EventCallback: Created callback object which can be used to
                stop listening.
        """

        if order is None:
            order = self.default_order

        callback = EventCallback(topic, callback, order)
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

        self._process_event(event)

    def _process_event(self, event):
        """Process event topic and trigger callbacks.

        Args:
            event (Event): Prepared event with topic and data.
        """

        callbacks = tuple(sorted(
            self._registered_callbacks, key=lambda x: x.order
        ))
        for callback in callbacks:
            callback.process_event(event)
            if not callback.is_ref_valid:
                self._registered_callbacks.remove(callback)


class QueuedEventSystem(EventSystem):
    """Events are automatically processed in queue.

    If callback triggers another event, the event is not processed until
    all callbacks of previous event are processed.

    Allows to implement custom event process loop by changing 'auto_execute'.

    Note:
        This probably should be default behavior of 'EventSystem'. Changing it
            now could cause problems in existing code.

    Args:
        auto_execute (Optional[bool]): If 'True', events are processed
            automatically. Custom loop calling 'process_next_event'
            must be implemented when set to 'False'.
    """

    def __init__(self, auto_execute=True):
        super(QueuedEventSystem, self).__init__()
        self._event_queue = collections.deque()
        self._current_event = None
        self._auto_execute = auto_execute

    def __len__(self):
        return self.count()

    def count(self):
        """Get number of events in queue.

        Returns:
            int: Number of events in queue.
        """

        return len(self._event_queue)

    def process_next_event(self):
        """Process next event in queue.

        Should be used only if 'auto_execute' is set to 'False'. Only single
            event is processed.

        Returns:
            Union[Event, None]: Processed event.
        """

        if self._current_event is not None:
            raise ValueError("An event is already in progress.")

        if not self._event_queue:
            return None
        event = self._event_queue.popleft()
        self._current_event = event
        self._process_event(event)
        self._current_event = None
        return event

    def emit_event(self, event):
        """Emit event object.

        Args:
           event (Event): Prepared event with topic and data.
        """

        if not self._auto_execute or self._current_event is not None:
            self._event_queue.append(event)
            return

        self._event_queue.append(event)
        while self._event_queue:
            event = self._event_queue.popleft()
            self._current_event = event
            self._process_event(event)
        self._current_event = None


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
