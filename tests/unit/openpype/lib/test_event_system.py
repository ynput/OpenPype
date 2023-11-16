from openpype.lib.events import EventSystem, QueuedEventSystem


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
