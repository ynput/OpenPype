import os
import tempfile
import inspect
import copy
from uuid import uuid4
from abc import ABCMeta, abstractmethod, abstractproperty

import six


TMP_FILE_PREFIX = "opw_tvp_"


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
        self, script, tmp_file_keys=None, output_dirs=None, data=None
    ):
        data = data or {}
        if not tmp_file_keys:
            tmp_file_keys = data.get("tmp_file_keys") or []

        if not output_dirs:
            output_dirs = data.get("output_dirs") or {}

        data["script"] = script
        data["tmp_file_keys"] = tmp_file_keys
        data["output_dirs"] = output_dirs
        self._script = script
        self._tmp_file_keys = tmp_file_keys
        self._output_dirs = output_dirs
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

        for key, dir_path in self._output_dirs.items():
            format_key = "{" + key + "}"
            dir_path = dir_path.replace("\\", "/")
            self._script.replace(format_key, dir_path)

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
        output_dirs = data.pop("output_dirs", None)
        return cls(script, tmp_file_keys, output_dirs, data)


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
        layers_by_id = {
            layer_data["layer_id"]: layer_data
            for layer_data in layers_data
        }
        layer_ids = tuple(layers_by_id.keys())
        pre_post_beh = get_layers_pre_post_behavior(
            layer_ids, communicator=self.communicator
        )
        exposure_frames = get_layers_exposure_frames(
            layer_ids, layers_data, communicator=self.communicator
        )
        output_layers_data = []
        for layer_data in layers_data:
            layer_id = layer_data["layer_id"]
            layer_data["exposure_frames"] = exposure_frames[layer_id]
            behaviors = pre_post_beh[layer_id]
            for key, value in behaviors.items():
                layer_data[key] = value
            output_layers_data.append(layer_data)

        self._result = {
            "layers_data": output_layers_data,
            "groups_data": groups_data,
            "scene_data": get_scene_data(self.communicator)
        }

    @classmethod
    def from_existing(cls, data):
        return cls(data)


class TVPaintCommands:
    def __init__(self, workfile, commands=None, communicator=None):
        if not commands:
            commands = []

        self._workfile = workfile
        self._commands = []
        self._communicator = communicator
        self._command_classes_by_name = None

        self.commands_from_data(commands)

    @property
    def communicator(self):
        return self._communicator

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
                    print("Skipping abstract class {}".format(attr.__name__))
                command_classes_by_name[attr.name] = attr
            self._command_classes_by_name = command_classes_by_name

        return self._command_classes_by_name

    def commands_from_data(self, commands_data):
        for command_data in commands_data:
            command_name = command_data["command"]

            klass = self.classes_by_name[command_name]
            command = klass.from_existing(command_data)
            self.add_command(command)

    def add_command(self, command):
        command.set_parent(self)
        self._commands.append(command)

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

    def result(self):
        return [
            command.result()
            for command in self._commands
        ]

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
