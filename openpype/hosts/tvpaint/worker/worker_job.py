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

    def __init__(self, parent, data):
        if data is None:
            data = {}
        else:
            data = copy.deepcopy(data)

        command_id = data.get("id")
        if command_id is None:
            command_id = str(uuid4())
        data["id"] = command_id
        data["command"] = self.name

        self._parent = parent
        self._result = None
        self._command_data = data
        self._done = False

    @property
    def id(self):
        return self._command_data["id"]

    @property
    def parent(self):
        return self._parent

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
    def from_existing(cls, parent, data):
        pass

    def execute_george(self, george_script):
        return self.parent.execute_george(george_script)

    def execute_george_through_file(self, george_script):
        return self.parent.execute_george_through_file(george_script)


class ExecuteSimpleGeorgeScript(BaseCommand):
    name = "execute_george_simple"

    def __init__(self, parent, script, data=None):
        data = data or {}
        data["script"] = script
        self._script = script
        super().__init__(parent, data)

    def execute(self):
        self._result = self.execute_george(self._script)

    @classmethod
    def from_existing(cls, parent, data):
        script = data.pop("script")
        return cls(parent, script, data)


class ExecuteGeorgeScript(BaseCommand):
    name = "execute_george_through_file"

    def __init__(self, parent, script, data=None):
        data = data or {}
        data["script"] = script
        self._script = script
        super().__init__(parent, data)

    def execute(self):
        self.execute_george_through_file(self._script)

    @classmethod
    def from_existing(cls, parent, data):
        script = data.pop("script")
        return cls(parent, script, data)


class ExecuteGeorgeScriptWithResult(BaseCommand):
    name = "execute_george_through_file_result"

    def __init__(self, parent, script, tmp_file_keys, data=None):
        data = data or {}
        data["script"] = script
        data["tmp_file_keys"] = tmp_file_keys
        self._script = script
        self._tmp_file_keys = tmp_file_keys
        super().__init__(parent, data)

    def execute(self):
        filepath_by_key = {}
        for key in self._tmp_file_keys:
            output_file = tempfile.NamedTemporaryFile(
                mode="w", prefix=TMP_FILE_PREFIX, suffix=".txt", delete=False
            )
            output_file.close()
            filepath_by_key[key] = output_file.name.replace("\\", "/")

        formatted_script = self._script.format(**filepath_by_key)
        self.execute_george_through_file(formatted_script)

        result = {}
        for key, filepath in filepath_by_key.items():
            with open(filepath, "r") as stream:
                data = stream.read()
            result[key] = data
            os.remove(filepath)

        self._result = result

    @classmethod
    def from_existing(cls, parent, data):
        script = data.pop("script")
        tmp_file_keys = data.pop("tmp_file_keys")
        return cls(parent, script, tmp_file_keys, data)


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
            command = klass.from_existing(self, command_data)
            self.add_command(command)

    def add_command(self, command):
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
