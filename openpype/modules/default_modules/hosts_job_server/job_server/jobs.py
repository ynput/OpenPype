import datetime
from uuid import uuid4


class Job:
    """Job related to specific host name.

    Data must contain everything needed to finish the job.
    """
    # Remove done jobs each n days to clear memory
    keep_in_memory_days = 3

    def __init__(self, host_name, data, job_id=None, created_time=None):
        if job_id is None:
            job_id = str(uuid4())
        self._id = job_id
        if created_time is None:
            created_time = datetime.datetime.now()
        self._created_time = created_time
        self._started_time = None
        self._done_time = None
        self.host_name = host_name
        self.data = data
        self._result_data = None

        self._started = False
        self._done = False
        self._errored = False
        self._message = None
        self._deleted = False

    def keep_in_memory(self):
        if self._done_time is None:
            return True

        now = datetime.datetime.now()
        delta = now - self._done_time
        return delta.days < self.keep_in_memory_days

    @property
    def id(self):
        return self._id

    @property
    def done(self):
        return self._done

    def reset(self):
        self._started = False
        self._started_time = None
        self._done = False
        self._done_time = None
        self._errored = False
        self._message = None

    @property
    def started(self):
        return self._started

    @property
    def deleted(self):
        return self._deleted

    def set_deleted(self):
        self._deleted = True

    def set_started(self):
        self._started_time = datetime.datetime.now()
        self._started = True

    def set_done(self, success=True, message=None, data=None):
        self._done = True
        self._done_time = datetime.datetime.now()
        self._errored = not success
        self._message = message
        self._result_data = data

    def status(self):
        output = {}
        if self._message:
            output["message"] = self._message

        state = "waiting"
        if self._deleted:
            state = "deleted"
        elif self._errored:
            state = "error"
        elif self._done:
            state = "done"
        elif self._started:
            state = "started"

        if self.done:
            output["result"] = self._result_data

        output["state"] = state

        return output
