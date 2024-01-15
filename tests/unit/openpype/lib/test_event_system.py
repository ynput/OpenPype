from functools import partial
from openpype.lib.events import (
    EventSystem,
    QueuedEventSystem,
    weakref_partial,
)


def test_default_event_system():
    output = []
    expected_output = [3, 2, 1]
    event_system = EventSystem()

    def callback_1():
        event_system.emit("topic.2", {}, None)
        output.append(1)

    def callback_2():
        event_system.emit("topic.3", {}, None)
        output.append(2)

    def callback_3():
        output.append(3)

    event_system.add_callback("topic.1", callback_1)
    event_system.add_callback("topic.2", callback_2)
    event_system.add_callback("topic.3", callback_3)

    event_system.emit("topic.1", {}, None)

    assert output == expected_output, (
        "Callbacks were not called in correct order")


def test_base_event_system_queue():
    output = []
    expected_output = [1, 2, 3]
    event_system = QueuedEventSystem()

    def callback_1():
        event_system.emit("topic.2", {}, None)
        output.append(1)

    def callback_2():
        event_system.emit("topic.3", {}, None)
        output.append(2)

    def callback_3():
        output.append(3)

    event_system.add_callback("topic.1", callback_1)
    event_system.add_callback("topic.2", callback_2)
    event_system.add_callback("topic.3", callback_3)

    event_system.emit("topic.1", {}, None)

    assert output == expected_output, (
        "Callbacks were not called in correct order")


def test_manual_event_system_queue():
    output = []
    expected_output = [1, 2, 3]
    event_system = QueuedEventSystem(auto_execute=False)

    def callback_1():
        event_system.emit("topic.2", {}, None)
        output.append(1)

    def callback_2():
        event_system.emit("topic.3", {}, None)
        output.append(2)

    def callback_3():
        output.append(3)

    event_system.add_callback("topic.1", callback_1)
    event_system.add_callback("topic.2", callback_2)
    event_system.add_callback("topic.3", callback_3)

    event_system.emit("topic.1", {}, None)

    while True:
        if event_system.process_next_event() is None:
            break

    assert output == expected_output, (
        "Callbacks were not called in correct order")


def test_unordered_events():
    """
    Validate if callbacks are triggered in order of their register.
    """

    result = []

    def function_a():
        result.append("A")

    def function_b():
        result.append("B")

    def function_c():
        result.append("C")

    # Without order
    event_system = QueuedEventSystem()
    event_system.add_callback("test", function_a)
    event_system.add_callback("test", function_b)
    event_system.add_callback("test", function_c)
    event_system.emit("test", {}, "test")

    assert result == ["A", "B", "C"]


def test_ordered_events():
    """
    Validate if callbacks are triggered by their order and order
        of their register.
    """
    result = []

    def function_a():
        result.append("A")

    def function_b():
        result.append("B")

    def function_c():
        result.append("C")

    def function_d():
        result.append("D")

    def function_e():
        result.append("E")

    def function_f():
        result.append("F")

    # Without order
    event_system = QueuedEventSystem()
    event_system.add_callback("test", function_a)
    event_system.add_callback("test", function_b, order=-10)
    event_system.add_callback("test", function_c, order=200)
    event_system.add_callback("test", function_d, order=150)
    event_system.add_callback("test", function_e)
    event_system.add_callback("test", function_f, order=200)
    event_system.emit("test", {}, "test")

    assert result == ["B", "A", "E", "D", "C", "F"]


def test_events_partial_callbacks():
    """
    Validate if partial callbacks are triggered.
    """

    result = []

    def function(name):
        result.append(name)

    def function_regular():
        result.append("regular")

    event_system = QueuedEventSystem()
    event_system.add_callback("test", function_regular)
    event_system.add_callback("test", partial(function, "foo"))
    event_system.add_callback("test", weakref_partial(function, "bar"))
    event_system.emit("test", {}, "test")

    # Delete function should also make partial callbacks invalid
    del function
    event_system.emit("test", {}, "test")

    assert result == ["regular", "bar", "regular"]
