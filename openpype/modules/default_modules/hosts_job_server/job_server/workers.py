from uuid import uuid4


class Worker:
    """Worker that can handle jobs of specific host."""
    def __init__(self, host_name):
        self._id = None
        self.host_name = host_name

    @property
    def id(self):
        if self._id is None:
            self._id = str(uuid4())
        return self._id
