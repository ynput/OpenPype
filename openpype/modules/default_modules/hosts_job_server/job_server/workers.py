from uuid import uuid4


class WorkerState:
    IDLE = object()
    JOB_ASSIGNED = object()
    JOB_SENT = object()


class Worker:
    """Worker that can handle jobs of specific host."""
    def __init__(self, host_name):
        self._id = None
        self.host_name = host_name
        self._state = WorkerState.IDLE

    @property
    def id(self):
        if self._id is None:
            self._id = str(uuid4())
        return self._id

    @property
    def state(self):
        return self._state

    def is_idle(self):
        return self._state is WorkerState.IDLE

    def job_assigned(self):
        return (
            self._state is WorkerState.JOB_ASSIGNED
            or self._state is WorkerState.JOB_SENT
        )

    def is_working(self):
        return self._state is WorkerState.JOB_SENT
