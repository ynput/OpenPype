### DEBUG PART
import os
import sys

pype_setup_path = "C:/Users/iLLiCiT/Desktop/Prace/pype-setup"
virtual_env_path = "C:/Users/Public/pype_env2"

environ_paths_str = os.environ.get("PYTHONPATH") or ""
environ_paths = environ_paths_str.split(os.pathsep)
environ_paths.extend([
    pype_setup_path,
    f"{virtual_env_path}/Lib/site-packages",
    f"{pype_setup_path}/vendor/python/acre",
    f"{pype_setup_path}/repos/pyblish-base",
    f"{pype_setup_path}/repos/pyblish-lite",
    f"{pype_setup_path}/repos/pype",
    f"{pype_setup_path}/repos/avalon-core",
    f"{pype_setup_path}/repos/pype/pype/tools"
])

new_env_environ_paths = []
for path in environ_paths:
    path = os.path.normpath(path)
    if path not in new_env_environ_paths:
        new_env_environ_paths.append(path)

envs = {
    "AVALON_CONFIG": "pype",
    "AVALON_DEBUG": "1",
    "AVALON_DB_DATA": f"{pype_setup_path}/../mongo_db_data",
    "AVALON_SCHEMA": f"{pype_setup_path}/repos/pype/schema",
    "AVALON_LABEL": "Pype",
    "AVALON_TIMEOUT": "1000",
    "AVALON_THUMBNAIL_ROOT": "D:/thumbnails",
    "AVALON_MONGO": "mongodb://localhost:2707",
    "AVALON_DB": "avalon",
    "PYPE_STUDIO_NAME": "Pype",
    "PYPE_PROJECT_CONFIGS": "",
    "PYPE_CONFIG": f"{pype_setup_path}/repos/pype-config",
    "PYPE_SETUP_PATH": pype_setup_path,
    "VIRTUAL_ENV": virtual_env_path,
    "PYTHONPATH": os.pathsep.join(new_env_environ_paths)
}

for key, value in envs.items():
    os.environ[key] = value
for path in environ_paths:
    if path not in sys.path:
        sys.path.append(path)
### DEBUG PART ENDED

import os
import re
import copy
import subprocess
import logging
import types
import platform
import getpass

import six
import acre

from pype.api import (
    system_settings,
    environments,
    Anatomy
)
import avalon.api


class ApplicationNotFound(Exception):
    pass


class ApplictionExecutableNotFound(Exception):
    pass


class ApplicationLaunchFailed(Exception):
    pass


def env_value_to_bool(env_key=None, value=None, default=False):
    if value is None and env_key is None:
        return default

    if value is None:
        value = os.environ.get(env_key)

    if value is not None:
        value = str(value).lower()
        if value in ("true", "yes", "1"):
            return True
        elif value in ("false", "no", "0"):
            return False
    return default


def compile_list_of_regexes(in_list):
    """Convert strings in entered list to compiled regex objects."""
    regexes = list()
    if not in_list:
        return regexes

    for item in in_list:
        if item:
            try:
                regexes.append(re.compile(item))
            except TypeError:
                print((
                    "Invalid type \"{}\" value \"{}\"."
                    " Expected string based object. Skipping."
                ).format(str(type(item)), str(item)))
    return regexes


class Application:
    def __init__(self, host_name, app_name, app_data, manager):
        self.manager = manager

        self.host_name = host_name
        self.app_name = app_name
        self.label = app_data["label"]
        self.variant_label = app_data["variant_label"] or None
        self.icon = app_data["icon"] or None

        self.enabled = app_data["enabled"]

        executables = app_data["executables"]
        if isinstance(executables, dict):
            executables = executables.get(platform.system().lower()) or []

        if not isinstance(executables, list):
            executables = [executables]
        self.executables = executables

    @property
    def full_label(self):
        if self.variant_label:
            return "{} {}".format(self.label, self.variant_label)
        return str(self.label)

    def find_executable(self):
        for executable_path in self.executables:
            if os.path.exists(executable_path):
                return executable_path
        return None

    def launch(self, project_name, asset_name, task_name):
        self.manager.launch(self.app_name, project_name, asset_name, task_name)


class ApplicationLaunchContext:
    def __init__(
        self, application, executable,
        project_name, asset_name, task_name,
        **data
    ):
        # Application object
        self.application = application

        # Logger
        logger_name = "{}-{}".format(self.__class__.__name__, self.app_name)
        self.log = logging.getLogger(logger_name)

        # Context
        self.project_name = project_name
        self.asset_name = asset_name
        self.task_name = task_name

        self.executable = executable

        self.data = dict(data)

        passed_env = self.data.pop("env", None)
        if passed_env is None:
            env = os.environ
        else:
            env = passed_env
        self.env = copy.deepcopy(env)

        # subprocess.Popen launch arguments (first argument in constructor)
        self.launch_args = [executable]
        # subprocess.Popen keyword arguments
        self.kwargs = {
            "env": self.env
        }

        if platform.system().lower() == "windows":
            # Detach new process from currently running process on Windows
            flags = (
                subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.DETACHED_PROCESS
            )
            self.kwargs["creationflags"] = flags

        self.process = None

        self.dbcon = avalon.api.AvalonMongoDB()
        self.dbcon.Session["AVALON_PROJECT"] = project_name
        self.dbcon.install()

        self.prepare_global_data()
        self.prepare_host_environments()
        self.prepare_context_environments()

    def __del__(self):
        # At least uninstall
        self.dbcon.uninstall()

    @property
    def app_name(self):
        return self.application.app_name

    @property
    def host_name(self):
        return self.application.host_name

    def launch(self):
        args = self.clear_launch_args(self.launch_args)
        self.process = subprocess.Popen(args, **self.kwargs)
        return self.process

    @staticmethod
    def clear_launch_args(args):
        while True:
            all_cleared = True
            new_args = []
            for arg in args:
                if isinstance(arg, (list, tuple, set)):
                    all_cleared = False
                    for _arg in arg:
                        new_args.append(_arg)
                else:
                    new_args.append(args)
            args = new_args

            if all_cleared:
                break
        return args

    def prepare_global_data(self):
        # Mongo documents
        project_doc = self.dbcon.find_one({"type": "project"})
        asset_doc = self.dbcon.find_one({
            "type": "asset",
            "name": self.asset_name
        })

        self.data["project_doc"] = project_doc
        self.data["asset_doc"] = asset_doc

        # Anatomy
        self.data["anatomy"] = Anatomy(self.project_name)

    def prepare_host_environments(self):
        passed_env = self.data.pop("env", None)
        if passed_env is None:
            env = os.environ
        else:
            env = passed_env
        env = copy.deepcopy(env)

        settings_env = self.data.get("settings_env")
        if settings_env is None:
            settings_env = environments()
            self.data["settings_env"] = settings_env

        # keys = (self.app_name, self.host_name)
        keys = ("global", "avalon", self.app_name, self.host_name)
        env_values = {}
        for env_key in keys:
            _env_values = settings_env.get(env_key)
            if not _env_values:
                continue

            tool_env = acre.parse(_env_values)
            env_values = acre.append(env_values, tool_env)

        final_env = acre.merge(acre.compute(env_values), current_env=self.env)
        self.env.update(final_env)

    def prepare_context_environments(self):
        # Context environments
        workdir_data = self.prepare_workdir_data()
        self.data["workdir_data"] = workdir_data

        hierarchy = workdir_data["hierarchy"]
        anatomy = self.data["anatomy"]

        try:
            anatomy_filled = anatomy.format(workdir_data)
            workdir = os.path.normpath(anatomy_filled["work"]["folder"])
            if not os.path.exists(workdir):
                os.makedirs(workdir)

        except Exception as exc:
            raise ApplicationLaunchFailed(
                "Error in anatomy.format: {}".format(str(exc))
            )

        context_env = {
            "AVALON_PROJECT": self.project_name,
            "AVALON_ASSET": self.asset_name,
            "AVALON_TASK": self.task_name,
            "AVALON_APP": self.host_name,
            "AVALON_APP_NAME": self.app_name,
            "AVALON_HIERARCHY": hierarchy,
            "AVALON_WORKDIR": workdir
        }
        self.env.update(context_env)

        self.prepare_last_workfile(workdir)

    def prepare_workdir_data(self):
        project_doc = self.data["project_doc"]
        asset_doc = self.data["asset_doc"]

        hierarchy = "/".join(asset_doc["data"]["parents"])

        data = {
            "project": {
                "name": project_doc["name"],
                "code": project_doc["data"].get("code")
            },
            "task": self.task_name,
            "asset": self.asset_name,
            "app": self.host_name,
            "hierarchy": hierarchy
        }
        return data

    def prepare_last_workfile(self, workdir):
        workdir_data = copy.deepcopy(self.data["workdir_data"])
        start_last_workfile = self.should_start_last_workfile(
            self.project_name, self.host_name, self.task_name
        )
        self.data["start_last_workfile"] = start_last_workfile

        # Store boolean as "0"(False) or "1"(True)
        self.env["AVALON_OPEN_LAST_WORKFILE"] = (
            str(int(bool(start_last_workfile)))
        )

        last_workfile_path = ""
        extensions = avalon.api.HOST_WORKFILE_EXTENSIONS.get(self.host_name)
        if extensions:
            anatomy = self.data["anatomy"]
            # Find last workfile
            file_template = anatomy.templates["work"]["file"]
            workdir_data.update({
                "version": 1,
                "user": os.environ.get("PYPE_USERNAME") or getpass.getuser(),
                "ext": extensions[0]
            })

            last_workfile_path = avalon.api.last_workfile(
                workdir, file_template, workdir_data, extensions, True
            )

        self.env["AVALON_LAST_WORKFILE"] = last_workfile_path
        self.data["last_workfile_path"] = last_workfile_path

    def should_start_last_workfile(self, project_name, host_name, task_name):
        """Define if host should start last version workfile if possible.

        Default output is `False`. Can be overriden with environment variable
        `AVALON_OPEN_LAST_WORKFILE`, valid values without case sensitivity are
        `"0", "1", "true", "false", "yes", "no"`.

        Args:
            project_name (str): Name of project.
            host_name (str): Name of host which is launched. In avalon's
                application context it's value stored in app definition under
                key `"application_dir"`. Is not case sensitive.
            task_name (str): Name of task which is used for launching the host.
                Task name is not case sensitive.

        Returns:
            bool: True if host should start workfile.

        """
        default_output = env_value_to_bool(
            "AVALON_OPEN_LAST_WORKFILE", default=False
        )
        # TODO convert to settings
        try:
            from pype.api import config
            startup_presets = (
                config.get_presets(project_name)
                .get("tools", {})
                .get("workfiles", {})
                .get("last_workfile_on_startup")
            )
        except Exception:
            startup_presets = None
            self.log.warning("Couldn't load pype's presets", exc_info=True)

        if not startup_presets:
            return default_output

        host_name_lowered = host_name.lower()
        task_name_lowered = task_name.lower()

        max_points = 2
        matching_points = -1
        matching_item = None
        for item in startup_presets:
            hosts = item.get("hosts") or tuple()
            tasks = item.get("tasks") or tuple()

            hosts_lowered = tuple(_host_name.lower() for _host_name in hosts)
            # Skip item if has set hosts and current host is not in
            if hosts_lowered and host_name_lowered not in hosts_lowered:
                continue

            tasks_lowered = tuple(_task_name.lower() for _task_name in tasks)
            # Skip item if has set tasks and current task is not in
            if tasks_lowered:
                task_match = False
                for task_regex in compile_list_of_regexes(tasks_lowered):
                    if re.match(task_regex, task_name_lowered):
                        task_match = True
                        break

                if not task_match:
                    continue

            points = int(bool(hosts_lowered)) + int(bool(tasks_lowered))
            if points > matching_points:
                matching_item = item
                matching_points = points

            if matching_points == max_points:
                break

        if matching_item is not None:
            output = matching_item.get("enabled")
            if output is None:
                output = default_output
            return output
        return default_output


class ApplicationManager:
    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)

        self.registered_hook_paths = []
        self.registered_hooks = []

        self.applications = {}

        self.refresh()

    def refresh(self):
        settings = system_settings()
        hosts_definitions = settings["global"]["applications"]
        for host_name, variant_definitions in hosts_definitions.items():
            enabled = variant_definitions["enabled"]
            label = variant_definitions.get("label") or host_name
            variants = variant_definitions.get("variants") or {}
            icon = variant_definitions.get("icon")
            for app_name, app_data in variants.items():
                # If host is disabled then disable all variants
                if not enabled:
                    app_data["enabled"] = enabled

                # Pass label from host definition
                if not app_data.get("label"):
                    app_data["label"] = label

                if not app_data.get("icon"):
                    app_data["icon"] = icon

                if app_name in self.applications:
                    raise AssertionError((
                        "BUG: Duplicated application name in settings \"{}\""
                    ).format(app_name))
                self.applications[app_name] = Application(
                    host_name, app_name, app_data, self
                )

    def launch(self, app_name, project_name, asset_name, task_name):
        app = self.applications.get(app_name)
        if not app:
            raise ApplicationNotFound(app_name)

        executable = app.find_executable()
        if not executable:
            raise ApplictionExecutableNotFound(app)

        context = ApplicationLaunchContext(
            app, executable, project_name, asset_name, task_name
        )
        # TODO pass context through launch hooks
        return context.launch()


if __name__ == "__main__":
    man = ApplicationManager()

    __app_name = "maya_2020"
    __project_name = "kuba_each_case"
    __asset_name = "Alpaca_01"
    __task_name = "animation"
    man.launch(__app_name, __project_name, __asset_name, __task_name)
