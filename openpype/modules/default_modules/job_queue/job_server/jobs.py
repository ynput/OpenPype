import datetime
import collections
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

        self._worker = None

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

        self._worker = None

    @property
    def started(self):
        return self._started

    @property
    def deleted(self):
        return self._deleted

    def set_deleted(self):
        self._deleted = True
        self.set_worker(None)

    def set_worker(self, worker):
        if worker is self._worker:
            return

        if self._worker is not None:
            self._worker.set_current_job(None)

        self._worker = worker
        if worker is not None:
            worker.set_current_job(self)

    def set_started(self):
        self._started_time = datetime.datetime.now()
        self._started = True

    def set_done(self, success=True, message=None, data=None):
        self._done = True
        self._done_time = datetime.datetime.now()
        self._errored = not success
        self._message = message
        self._result_data = data
        if self._worker is not None:
            self._worker.set_current_job(None)

    def status(self):
        worker_id = None
        if self._worker is not None:
            worker_id = self._worker.id
        output = {
            "id": self.id,
            "worker_id": worker_id,
            "done": self._done
        }
        output["message"] = self._message or None

        state = "waiting"
        if self._deleted:
            state = "deleted"
        elif self._errored:
            state = "error"
        elif self._done:
            state = "done"
        elif self._started:
            state = "started"

        output["result"] = self._result_data

        output["state"] = state

        return output


class JobQueue:
    """Queue holds jobs that should be done and workers that can do them.

    Also asign jobs to a worker.
    """
    old_jobs_check_minutes_interval = 30

    def __init__(self):
        self._last_old_jobs_check = datetime.datetime.now()
        self._jobs_by_id = {}
        self._job_queue_by_host_name = collections.defaultdict(
            collections.deque
        )
        self._workers_by_id = {}
        self._workers_by_host_name = collections.defaultdict(list)

    def workers(self):
        """All currently registered workers."""
        return self._workers_by_id.values()

    def add_worker(self, worker):
        host_name = worker.host_name
        print("Added new worker for \"{}\"".format(host_name))
        self._workers_by_id[worker.id] = worker
        self._workers_by_host_name[host_name].append(worker)

    def get_worker(self, worker_id):
        return self._workers_by_id.get(worker_id)

    def remove_worker(self, worker):
        # Look if worker had assigned job to do
        job = worker.current_job
        if job is not None and not job.done:
            # Reset job
            job.set_worker(None)
            job.reset()
            # Add job back to queue
            self._job_queue_by_host_name[job.host_name].appendleft(job)

        # Remove worker from registered workers
        self._workers_by_id.pop(worker.id, None)
        host_name = worker.host_name
        if worker in self._workers_by_host_name[host_name]:
            self._workers_by_host_name[host_name].remove(worker)

        print("Removed worker for \"{}\"".format(host_name))

    def assign_jobs(self):
        """Try to assign job for each idle worker.

        Error all jobs without needed worker.
        """
        available_host_names = set()
        for worker in self._workers_by_id.values():
            host_name = worker.host_name
            available_host_names.add(host_name)
            if worker.is_idle():
                jobs = self._job_queue_by_host_name[host_name]
                while jobs:
                    job = jobs.popleft()
                    if not job.deleted:
                        worker.set_current_job(job)
                        break

        for host_name in tuple(self._job_queue_by_host_name.keys()):
            if host_name in available_host_names:
                continue

            jobs_deque = self._job_queue_by_host_name[host_name]
            message = ("Not available workers for \"{}\"").format(host_name)
            while jobs_deque:
                job = jobs_deque.popleft()
                if not job.deleted:
                    job.set_done(False, message)
        self._remove_old_jobs()

    def get_jobs(self):
        return self._jobs_by_id.values()

    def get_job(self, job_id):
        """Job by it's id."""
        return self._jobs_by_id.get(job_id)

    def create_job(self, host_name, job_data):
        """Create new job from passed data and add it to queue."""
        job = Job(host_name, job_data)
        self._jobs_by_id[job.id] = job
        self._job_queue_by_host_name[host_name].append(job)
        return job

    def _remove_old_jobs(self):
        """Once in specific time look if should remove old finished jobs."""
        delta = datetime.datetime.now() - self._last_old_jobs_check
        if delta.seconds < self.old_jobs_check_minutes_interval:
            return

        for job_id in tuple(self._jobs_by_id.keys()):
            job = self._jobs_by_id[job_id]
            if not job.keep_in_memory():
                self._jobs_by_id.pop(job_id)

    def remove_job(self, job_id):
        """Delete job and eventually stop it."""
        job = self._jobs_by_id.get(job_id)
        if job is None:
            return

        job.set_deleted()
        self._jobs_by_id.pop(job.id)

    def get_job_status(self, job_id):
        """Job's status based on id."""
        job = self._jobs_by_id.get(job_id)
        if job is None:
            return {}
        return job.status()
