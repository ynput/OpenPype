"""Events holding data about specific event."""


class BaseEvent:
    """Base event object.

    Can be used to anything because data are not much specific. Only required
    argument is topic which defines why event is happening and may be used for
    filtering.

    Arg:
        topic (str): Identifier of event.
        data (Any): Data specific for event. Dictionary is recommended.
    """
    _data = {}

    def __init__(self, topic, data=None):
        self._topic = topic
        if data is None:
            data = {}
        self._data = data

    @property
    def data(self):
        return self._data

    @property
    def topic(self):
        return self._topic


class BeforeWorkfileSave(BaseEvent):
    """Before workfile changes event data."""
    def __init__(self, new_workfile, workdir):
        super(BeforeWorkfileSave, self).__init__("before.workfile.save")

        self.workfile_path = new_workfile
        self.workdir_path = workdir
