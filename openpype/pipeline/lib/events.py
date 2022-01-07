"""Events holding data about specific event."""


# Inherit from 'object' for Python 2 hosts
class BaseEvent(object):
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

    @classmethod
    def emit(cls, *args, **kwargs):
        """Create object of event and emit.

        Args:
            Same args as '__init__' expects which may be class specific.
        """
        from avalon import pipeline

        obj = cls(*args, **kwargs)
        pipeline.emit(obj.topic, [obj])
        return obj


class BeforeWorkfileSave(BaseEvent):
    """Before workfile changes event data."""
    def __init__(self, filename, workdir):
        super(BeforeWorkfileSave, self).__init__("before.workfile.save")
        self.filename = filename
        self.workdir_path = workdir
