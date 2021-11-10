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
    @abstractproperty
    def name(self):
        """Command name (must be unique)."""
        pass

    def __init__(self, data=None):
        if data is None:
            data = {}
        else:
            data = copy.deepcopy(data)

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
        if self._parent is None:
            return None
        return self._parent.job_queue_root()

    def set_parent(self, parent):
        self._parent = parent

    @property
    def id(self):
        return self._command_data["id"]

    @property
    def parent(self):
        return self._parent

    @property
    def communicator(self):
        return self._parent.communicator

    @property
    def done(self):
        return self._done

    def set_done(self):
        self._done = True

    def set_result(self, result):
        self._result = result

    def result(self):
        return {
            "id": self.id,
            "result": self._result,
            "done": self._done
        }

    def command_data(self):
        return copy.deepcopy(self._command_data)

    @abstractmethod
    def execute(self):
        pass

    @classmethod
    @abstractmethod
    def from_existing(cls, data):
        pass

    def execute_george(self, george_script):
        return self.parent.execute_george(george_script)

    def execute_george_through_file(self, george_script):
        return self.parent.execute_george_through_file(george_script)


class ExecuteSimpleGeorgeScript(BaseCommand):
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
    name = "execute_george_through_file"

    def __init__(
        self, script, tmp_file_keys=None, root_dir_key=None, data=None
    ):
        data = data or {}
        if not tmp_file_keys:
            tmp_file_keys = data.get("tmp_file_keys") or []

        data["script"] = script
        data["tmp_file_keys"] = tmp_file_keys
        data["root_dir_key"] = root_dir_key
        self._script = script
        self._tmp_file_keys = tmp_file_keys
        self._root_dir_key = root_dir_key
        super().__init__(data)

    def execute(self):
        filepath_by_key = {}
        for key in self._tmp_file_keys:
            output_file = tempfile.NamedTemporaryFile(
                mode="w", prefix=TMP_FILE_PREFIX, suffix=".txt", delete=False
            )
            output_file.close()
            format_key = "{" + key + "}"
            output_path = output_file.name.replace("\\", "/")
            self._script.replace(format_key, output_path)
            filepath_by_key[key] = output_path

        if self._root_dir_key:
            job_queue_root = self.job_queue_root()
            format_key = "{" + self._root_dir_key + "}"
            self._script.replace(format_key, job_queue_root.replace("\\", "/"))

        self.execute_george_through_file(self._script)

        result = {}
        for key, filepath in filepath_by_key.items():
            with open(filepath, "r") as stream:
                data = stream.read()
            result[key] = data
            os.remove(filepath)

        self._result = result

    @classmethod
    def from_existing(cls, data):
        script = data.pop("script")
        tmp_file_keys = data.pop("tmp_file_keys", None)
        root_dir_key = data.pop("root_dir_key", None)
        return cls(script, tmp_file_keys, root_dir_key, data)


class CollectSceneData(BaseCommand):
    name = "collect_scene_data"

    def execute(self):
        from avalon.tvpaint.lib import (
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


class TVPaintCommands:
    def __init__(self, workfile, job_queue_module=None):
        self._log = None
        self._workfile = workfile
        self._commands = []
        self._command_classes_by_name = None
        if job_queue_module is None:
            manager = ModulesManager()
            job_queue_module = manager.modules_by_name["job_queue"]
        self._job_queue_module = job_queue_module

    def job_queue_root(self):
        return self._job_queue_module.get_jobs_root_from_settings()

    @property
    def log(self):
        if self._log is None:
            self._log = PypeLogger.get_logger(self.__class__.__name__)
        return self._log

    @property
    def classes_by_name(self):
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
        command.set_parent(self)
        self._commands.append(command)

    def result(self):
        return [
            command.result()
            for command in self._commands
        ]


class SenderTVPaintCommands(TVPaintCommands):
    def commands_data(self):
        return [
            command.command_data()
            for command in self._commands
        ]

    def to_job_data(self):
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
        job_id = self._send_job()
        while True:
            job_status = self._job_queue_module.get_job_status(job_id)
            if job_status["done"]:
                break
            time.sleep(0.3)

        # Check if job state is done
        if job_status["state"] != "done":
            raise JobFailed(job_status)

        self.set_result(job_status["result"])

        self.log.debug("Job is done and result is stored.")


class ProcessTVPaintCommands(TVPaintCommands):
    def __init__(self, workfile, commands, communicator):
        super(ProcessTVPaintCommands, self).__init__(workfile)

        self._communicator = communicator

        self.commands_from_data(commands)

    @property
    def communicator(self):
        return self._communicator

    def commands_from_data(self, commands_data):
        for command_data in commands_data:
            command_name = command_data["command"]

            klass = self.classes_by_name[command_name]
            command = klass.from_existing(command_data)
            self.add_command(command)

    def execute_george(self, george_script):
        return self.communicator.execute_george(george_script)

    def execute_george_through_file(self, george_script):
        temporary_file = tempfile.NamedTemporaryFile(
            mode="w", prefix=TMP_FILE_PREFIX, suffix=".grg", delete=False
        )
        temporary_file.write(george_script)
        temporary_file.close()
        temp_file_path = temporary_file.name.replace("\\", "/")
        self.execute_george("tv_runscript {}".format(temp_file_path))
        os.remove(temp_file_path)

    def _open_workfile(self):
        workfile = self._workfile.replace("\\", "/")
        print("Opening workfile {}".format(workfile))
        george_script = "tv_LoadProject '\"'\"{}\"'\"'".format(workfile)
        self.execute_george_through_file(george_script)

    def _close_workfile(self):
        print("Closing workfile")
        self.execute_george_through_file("tv_projectclose")

    def execute(self):
        self._open_workfile()
        print("Commands execution started ({})".format(len(self._commands)))
        for command in self._commands:
            command.execute()
            command.set_done()
        self._close_workfile()
