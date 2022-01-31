import os
import tempfile
import inspect
import copy
import json
import time
from uuid import uuid4
from abc import ABCMeta, abstractmethod, abstractproperty

import six

from openpype.api import PypeLogger
from openpype.modules import ModulesManager


TMP_FILE_PREFIX = "opw_tvp_"


class JobFailed(Exception):
    """Raised when job was sent and finished unsuccessfully."""
    def __init__(self, job_status):
        job_state = job_status["state"]
        job_message = job_status["message"] or "Unknown issue"
        error_msg = (
            "Job didn't finish properly."
            " Job state: \"{}\" | Job message: \"{}\""
        ).format(job_state, job_message)

        self.job_status = job_status

        super().__init__(error_msg)


@six.add_metaclass(ABCMeta)
class BaseCommand:
    """Abstract TVPaint command which can be executed through worker.

    Each command must have unique name and implemented 'execute' and
    'from_existing' methods.

    Command also have id which is created on command creation.

    The idea is that command is just a data container on sender side send
    through server to a worker where is replicated one by one, executed and
    result sent back to sender through server.
    """
    @abstractproperty
    def name(self):
        """Command name (must be unique)."""
        pass

    def __init__(self, data=None):
        if data is None:
            data = {}
        else:
            data = copy.deepcopy(data)

        # Use 'id' from data when replicating on process side
        command_id = data.get("id")
        if command_id is None:
            command_id = str(uuid4())
        data["id"] = command_id
        data["command"] = self.name

        self._parent = None
        self._result = None
        self._command_data = data
        self._done = False

    def job_queue_root(self):
        """Access to job queue root.

        Job queue root is shared access point to files shared across senders
        and workers.
        """
        if self._parent is None:
            return None
        return self._parent.job_queue_root()

    def set_parent(self, parent):
        self._parent = parent

    @property
    def id(self):
        """Command id."""
        return self._command_data["id"]

    @property
    def parent(self):
        """Parent of command expected type of 'TVPaintCommands'."""
        return self._parent

    @property
    def communicator(self):
        """TVPaint communicator.

        Available only on worker side.
        """
        return self._parent.communicator

    @property
    def done(self):
        """Is command done."""
        return self._done

    def set_done(self):
        """Change state of done."""
        self._done = True

    def set_result(self, result):
        """Set result of executed command."""
        self._result = result

    def result(self):
        """Result of command."""
        return copy.deepcopy(self._result)

    def response_data(self):
        """Data send as response to sender."""
        return {
            "id": self.id,
            "result": self._result,
            "done": self._done
        }

    def command_data(self):
        """Raw command data."""
        return copy.deepcopy(self._command_data)

    @abstractmethod
    def execute(self):
        """Execute command on worker side."""
        pass

    @classmethod
    @abstractmethod
    def from_existing(cls, data):
        """Recreate object based on passed data."""
        pass

    def execute_george(self, george_script):
        """Execute george script in TVPaint."""
        return self.parent.execute_george(george_script)

    def execute_george_through_file(self, george_script):
        """Execute george script through temp file in TVPaint."""
        return self.parent.execute_george_through_file(george_script)


class ExecuteSimpleGeorgeScript(BaseCommand):
    """Execute simple george script in TVPaint.

    Args:
        script(str): Script that will be executed.
    """
    name = "execute_george_simple"

    def __init__(self, script, data=None):
        data = data or {}
        data["script"] = script
        self._script = script
        super().__init__(data)

    def execute(self):
        self._result = self.execute_george(self._script)

    @classmethod
    def from_existing(cls, data):
        script = data.pop("script")
        return cls(script, data)


class ExecuteGeorgeScript(BaseCommand):
    """Execute multiline george script in TVPaint.

    Args:
        script_lines(list): Lines that will be executed in george script
            through temp george file.
        tmp_file_keys(list): List of formatting keys in george script that
            require replacement with path to a temp file where result will be
            stored. The content of file is stored to result by the key.
        root_dir_key(str): Formatting key that will be replaced in george
            script with job queue root which can be different on worker side.
        data(dict): Raw data about command.
    """
    name = "execute_george_through_file"

    def __init__(
        self, script_lines, tmp_file_keys=None, root_dir_key=None, data=None
    ):
        data = data or {}
        if not tmp_file_keys:
            tmp_file_keys = data.get("tmp_file_keys") or []

        data["script_lines"] = script_lines
        data["tmp_file_keys"] = tmp_file_keys
        data["root_dir_key"] = root_dir_key
        self._script_lines = script_lines
        self._tmp_file_keys = tmp_file_keys
        self._root_dir_key = root_dir_key
        super().__init__(data)

    def execute(self):
        filepath_by_key = {}
        script = self._script_lines
        if isinstance(script, list):
            script = "\n".join(script)

        # Replace temporary files in george script
        for key in self._tmp_file_keys:
            output_file = tempfile.NamedTemporaryFile(
                mode="w", prefix=TMP_FILE_PREFIX, suffix=".txt", delete=False
            )
            output_file.close()
            format_key = "{" + key + "}"
            output_path = output_file.name.replace("\\", "/")
            script = script.replace(format_key, output_path)
            filepath_by_key[key] = output_path

        # Replace job queue root in script
        if self._root_dir_key:
            job_queue_root = self.job_queue_root()
            format_key = "{" + self._root_dir_key + "}"
            script = script.replace(
                format_key, job_queue_root.replace("\\", "/")
            )

        # Execute the script
        self.execute_george_through_file(script)

        # Store result of temporary files
        result = {}
        for key, filepath in filepath_by_key.items():
            with open(filepath, "r") as stream:
                data = stream.read()
            result[key] = data
            os.remove(filepath)

        self._result = result

    @classmethod
    def from_existing(cls, data):
        """Recreate the object from data."""
        script_lines = data.pop("script_lines")
        tmp_file_keys = data.pop("tmp_file_keys", None)
        root_dir_key = data.pop("root_dir_key", None)
        return cls(script_lines, tmp_file_keys, root_dir_key, data)


class CollectSceneData(BaseCommand):
    """Helper command which will collect all useful info about workfile.

    Result is dictionary with all layers data, exposure frames by layer ids
    pre/post behavior of layers by their ids, group information and scene data.
    """
    name = "collect_scene_data"

    def execute(self):
        from openpype.hosts.tvpaint.api.lib import (
            get_layers_data,
            get_groups_data,
            get_layers_pre_post_behavior,
            get_layers_exposure_frames,
            get_scene_data
        )

        groups_data = get_groups_data(communicator=self.communicator)
        layers_data = get_layers_data(communicator=self.communicator)
        layer_ids = [
            layer_data["layer_id"]
            for layer_data in layers_data
        ]
        pre_post_beh_by_layer_id = get_layers_pre_post_behavior(
            layer_ids, communicator=self.communicator
        )
        exposure_frames_by_layer_id = get_layers_exposure_frames(
            layer_ids, layers_data, communicator=self.communicator
        )

        self._result = {
            "layers_data": layers_data,
            "exposure_frames_by_layer_id": exposure_frames_by_layer_id,
            "pre_post_beh_by_layer_id": pre_post_beh_by_layer_id,
            "groups_data": groups_data,
            "scene_data": get_scene_data(self.communicator)
        }

    @classmethod
    def from_existing(cls, data):
        return cls(data)


@six.add_metaclass(ABCMeta)
class TVPaintCommands:
    """Wrapper around TVPaint commands to be able send multiple commands.

    Commands may send one or multiple commands at once. Also gives api access
    for commands info.

    Base for sender and receiver which are extending the logic for their
    purposes. One of differences is preparation of workfile path.

    Args:
        workfile(str): Path to workfile.
        job_queue_module(JobQueueModule): Object of OpenPype module JobQueue.
    """
    def __init__(self, workfile, job_queue_module=None):
        self._log = None
        self._commands = []
        self._command_classes_by_name = None
        if job_queue_module is None:
            manager = ModulesManager()
            job_queue_module = manager.modules_by_name["job_queue"]
        self._job_queue_module = job_queue_module

        self._workfile = self._prepare_workfile(workfile)

    @abstractmethod
    def _prepare_workfile(self, workfile):
        """Modification of workfile path on initialization to match platorm."""
        pass

    def job_queue_root(self):
        """Job queue root for current platform using current settings."""
        return self._job_queue_module.get_jobs_root_from_settings()

    @property
    def log(self):
        """Access to logger object."""
        if self._log is None:
            self._log = PypeLogger.get_logger(self.__class__.__name__)
        return self._log

    @property
    def classes_by_name(self):
        """Prepare commands classes for validation and recreation of commands.

        It is expected that all commands are defined in this python file so
        we're looking for all implementation of BaseCommand in globals.
        """
        if self._command_classes_by_name is None:
            command_classes_by_name = {}
            for attr in globals().values():
                if (
                    not inspect.isclass(attr)
                    or not issubclass(attr, BaseCommand)
                    or attr is BaseCommand
                ):
                    continue

                if inspect.isabstract(attr):
                    self.log.debug(
                        "Skipping abstract class {}".format(attr.__name__)
                    )
                command_classes_by_name[attr.name] = attr
            self._command_classes_by_name = command_classes_by_name

        return self._command_classes_by_name

    def add_command(self, command):
        """Add command to process."""
        command.set_parent(self)
        self._commands.append(command)

    def result(self):
        """Result of commands in list in which they were processed."""
        return [
            command.result()
            for command in self._commands
        ]

    def response_data(self):
        """Data which should be send from worker."""
        return [
            command.response_data()
            for command in self._commands
        ]


class SenderTVPaintCommands(TVPaintCommands):
    """Sender implementation of TVPaint Commands."""
    def _prepare_workfile(self, workfile):
        """Remove job queue root from workfile path.

        It is expected that worker will add it's root before passed workfile.
        """
        new_workfile = workfile.replace("\\", "/")
        job_queue_root = self.job_queue_root().replace("\\", "/")
        if job_queue_root not in new_workfile:
            raise ValueError((
                "Workfile is not located in JobQueue root."
                " Workfile path: \"{}\". JobQueue root: \"{}\""
            ).format(workfile, job_queue_root))
        return new_workfile.replace(job_queue_root, "")

    def commands_data(self):
        """Commands data to be able recreate them."""
        return [
            command.command_data()
            for command in self._commands
        ]

    def to_job_data(self):
        """Convert commands to job data before sending to workers server."""
        return {
            "workfile": self._workfile,
            "function": "commands",
            "commands": self.commands_data()
        }

    def set_result(self, result):
        commands_by_id = {
            command.id: command
            for command in self._commands
        }

        for item in result:
            command = commands_by_id[item["id"]]
            command.set_result(item["result"])
            command.set_done()

    def _send_job(self):
        """Send job to a workers server."""
        # Send job data to job queue server
        job_data = self.to_job_data()
        self.log.debug("Sending job to JobQueue server.\n{}".format(
            json.dumps(job_data, indent=4)
        ))
        job_id = self._job_queue_module.send_job("tvpaint", job_data)
        self.log.info((
            "Job sent to JobQueue server and got id \"{}\"."
            " Waiting for finishing the job."
        ).format(job_id))

        return job_id

    def send_job_and_wait(self):
        """Send job to workers server and wait for response.

        Result of job is stored into the object.

        Raises:
            JobFailed: When job was finished but not successfully.
        """
        job_id = self._send_job()
        while True:
            job_status = self._job_queue_module.get_job_status(job_id)
            if job_status["done"]:
                break
            time.sleep(1)

        # Check if job state is done
        if job_status["state"] != "done":
            raise JobFailed(job_status)

        self.set_result(job_status["result"])

        self.log.debug("Job is done and result is stored.")


class ProcessTVPaintCommands(TVPaintCommands):
    """Worker side of TVPaint Commands.

    It is expected this object is created only on worker's side from existing
    data loaded from job.

    Workfile path logic is based on 'SenderTVPaintCommands'.
    """
    def __init__(self, workfile, commands, communicator):
        super(ProcessTVPaintCommands, self).__init__(workfile)

        self._communicator = communicator

        self.commands_from_data(commands)

    def _prepare_workfile(self, workfile):
        """Preprend job queue root before passed workfile."""
        workfile = workfile.replace("\\", "/")
        job_queue_root = self.job_queue_root().replace("\\", "/")
        new_workfile = "/".join([job_queue_root, workfile])
        while "//" in new_workfile:
            new_workfile = new_workfile.replace("//", "/")
        return os.path.normpath(new_workfile)

    @property
    def communicator(self):
        """Access to TVPaint communicator."""
        return self._communicator

    def commands_from_data(self, commands_data):
        """Recreate command from passed data."""
        for command_data in commands_data:
            command_name = command_data["command"]

            klass = self.classes_by_name[command_name]
            command = klass.from_existing(command_data)
            self.add_command(command)

    def execute_george(self, george_script):
        """Helper method to execute george script."""
        return self.communicator.execute_george(george_script)

    def execute_george_through_file(self, george_script):
        """Helper method to execute george script through temp file."""
        temporary_file = tempfile.NamedTemporaryFile(
            mode="w", prefix=TMP_FILE_PREFIX, suffix=".grg", delete=False
        )
        temporary_file.write(george_script)
        temporary_file.close()
        temp_file_path = temporary_file.name.replace("\\", "/")
        self.execute_george("tv_runscript {}".format(temp_file_path))
        os.remove(temp_file_path)

    def _open_workfile(self):
        """Open workfile in TVPaint."""
        workfile = self._workfile
        print("Opening workfile {}".format(workfile))
        george_script = "tv_LoadProject '\"'\"{}\"'\"'".format(workfile)
        self.execute_george_through_file(george_script)

    def _close_workfile(self):
        """Close workfile in TVPaint."""
        print("Closing workfile")
        self.execute_george_through_file("tv_projectclose")

    def execute(self):
        """Execute commands."""
        # First open the workfile
        self._open_workfile()
        # Execute commands one by one
        # TODO maybe stop processing when command fails?
        print("Commands execution started ({})".format(len(self._commands)))
        for command in self._commands:
            command.execute()
            command.set_done()
        # Finally close workfile
        self._close_workfile()
