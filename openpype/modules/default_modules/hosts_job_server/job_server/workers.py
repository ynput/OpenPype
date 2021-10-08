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
        self._job = None


    @property
    def id(self):
        if self._id is None:
            self._id = str(uuid4())
        return self._id

    @property
    def state(self):
        return self._state

    @property
    def current_job(self):
        return self._job

    def is_idle(self):
        return self._state is WorkerState.IDLE

    def job_assigned(self):
        return (
            self._state is WorkerState.JOB_ASSIGNED
            or self._state is WorkerState.JOB_SENT
        )

    def is_working(self):
        return self._state is WorkerState.JOB_SENT

    def set_current_job(self, job):
        if job is self._job:
            return

        self._job = job
        if job is None:
            self._set_idle()
        else:
            self._state = WorkerState.JOB_ASSIGNED
            job.set_worker(self)

    def _set_idle(self):
        self._job = None
        self._state = WorkerState.IDLE

    def set_working(self):
        self._state = WorkerState.JOB_SENT
