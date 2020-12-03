import os
import re
import json
import getpass
import copy

from pype.api import (
    Anatomy,
    get_project_settings
)
from pype.lib import (
    env_value_to_bool,
    PreLaunchHook,
    ApplicationLaunchFailed
)

import acre
import avalon.api


class GlobalHostDataHook(PreLaunchHook):
    order = -100

    def execute(self):
        """Prepare global objects to `data` that will be used for sure."""
        if not self.application.is_host:
            self.log.info(
                "Skipped hook {}. Application is not marked as host.".format(
                    self.__class__.__name__
                )
            )
            return

        self.prepare_global_data()
        self.prepare_host_environments()
        self.prepare_context_environments()

    def prepare_global_data(self):
        """Prepare global objects to `data` that will be used for sure."""
        # Mongo documents
        project_name = self.data.get("project_name")
        if not project_name:
            self.log.info(
                "Skipping global data preparation."
                " Key `project_name` was not found in launch context."
            )
            return

        self.log.debug("Project name is set to \"{}\"".format(project_name))
        # Anatomy
        self.data["anatomy"] = Anatomy(project_name)

        # Mongo connection
        dbcon = avalon.api.AvalonMongoDB()
        dbcon.Session["AVALON_PROJECT"] = project_name
        dbcon.install()

        self.data["dbcon"] = dbcon

        # Project document
        project_doc = dbcon.find_one({"type": "project"})
        self.data["project_doc"] = project_doc

        asset_name = self.data.get("asset_name")
        if not asset_name:
            self.log.warning(
                "Asset name was not set. Skipping asset document query."
            )
            return

        asset_doc = dbcon.find_one({
            "type": "asset",
            "name": asset_name
        })
        self.data["asset_doc"] = asset_doc

    def _merge_env(self, env, current_env):
        """Modified function(merge) from acre module."""
        result = current_env.copy()
        for key, value in env.items():
            # Keep missing keys by not filling `missing` kwarg
            value = acre.lib.partial_format(value, data=current_env)
            result[key] = value
        return result

    def prepare_host_environments(self):
        """Modify launch environments based on launched app and context."""
        # Keys for getting environments
        env_keys = [self.app_group, self.app_name]

        asset_doc = self.data.get("asset_doc")
        if asset_doc:
            # Add tools environments
            for key in asset_doc["data"].get("tools_env") or []:
                tool = self.manager.tools.get(key)
                if tool:
                    if tool.group_name not in env_keys:
                        env_keys.append(tool.group_name)

                    if tool.name not in env_keys:
                        env_keys.append(tool.name)

        self.log.debug(
            "Finding environment groups for keys: {}".format(env_keys)
        )

        settings_env = self.data["settings_env"]
        env_values = {}
        for env_key in env_keys:
            _env_values = settings_env.get(env_key)
            if not _env_values:
                continue

            # Choose right platform
            tool_env = acre.parse(_env_values)
            # Merge dictionaries
            env_values = self._merge_env(tool_env, env_values)

        final_env = self._merge_env(
            acre.compute(env_values), self.launch_context.env
        )

        # Update env
        self.launch_context.env.update(final_env)

    def prepare_context_environments(self):
        """Modify launch environemnts with context data for launched host."""
        # Context environments
        project_doc = self.data.get("project_doc")
        asset_doc = self.data.get("asset_doc")
        task_name = self.data.get("task_name")
        if (
            not project_doc
            or not asset_doc
            or not task_name
        ):
            self.log.info(
                "Skipping context environments preparation."
                " Launch context does not contain required data."
            )
            return

        workdir_data = self._prepare_workdir_data(
            project_doc, asset_doc, task_name
        )
        self.data["workdir_data"] = workdir_data

        hierarchy = workdir_data["hierarchy"]
        anatomy = self.data["anatomy"]

        try:
            anatomy_filled = anatomy.format(workdir_data)
            workdir = os.path.normpath(anatomy_filled["work"]["folder"])
            if not os.path.exists(workdir):
                self.log.debug(
                    "Creating workdir folder: \"{}\"".format(workdir)
                )
                os.makedirs(workdir)

        except Exception as exc:
            raise ApplicationLaunchFailed(
                "Error in anatomy.format: {}".format(str(exc))
            )

        context_env = {
            "AVALON_PROJECT": project_doc["name"],
            "AVALON_ASSET": asset_doc["name"],
            "AVALON_TASK": task_name,
            "AVALON_APP": self.host_name,
            "AVALON_APP_NAME": self.app_name,
            "AVALON_HIERARCHY": hierarchy,
            "AVALON_WORKDIR": workdir
        }
        self.log.debug(
            "Context environemnts set:\n{}".format(
                json.dumps(context_env, indent=4)
            )
        )
        self.launch_context.env.update(context_env)

        self.prepare_last_workfile(workdir)

    def _prepare_workdir_data(self, project_doc, asset_doc, task_name):
        hierarchy = "/".join(asset_doc["data"]["parents"])

        data = {
            "project": {
                "name": project_doc["name"],
                "code": project_doc["data"].get("code")
            },
            "task": task_name,
            "asset": asset_doc["name"],
            "app": self.host_name,
            "hierarchy": hierarchy
        }
        return data

    def prepare_last_workfile(self, workdir):
        """last workfile workflow preparation.

        Function check if should care about last workfile workflow and tries
        to find the last workfile. Both information are stored to `data` and
        environments.

        Last workfile is filled always (with version 1) even if any workfile
        exists yet.

        Args:
            workdir (str): Path to folder where workfiles should be stored.
        """
        _workdir_data = self.data.get("workdir_data")
        if not _workdir_data:
            self.log.info(
                "Skipping last workfile preparation."
                " Key `workdir_data` not filled."
            )
            return

        workdir_data = copy.deepcopy(_workdir_data)
        project_name = self.data["project_name"]
        task_name = self.data["task_name"]
        start_last_workfile = self.should_start_last_workfile(
            project_name, self.host_name, task_name
        )
        self.data["start_last_workfile"] = start_last_workfile

        # Store boolean as "0"(False) or "1"(True)
        self.launch_context.env["AVALON_OPEN_LAST_WORKFILE"] = (
            str(int(bool(start_last_workfile)))
        )

        _sub_msg = "" if start_last_workfile else " not"
        self.log.debug(
            "Last workfile should{} be opened on start.".format(_sub_msg)
        )

        # Last workfile path
        last_workfile_path = ""
        extensions = avalon.api.HOST_WORKFILE_EXTENSIONS.get(
            self.host_name
        )
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

        if os.path.exists(last_workfile_path):
            self.log.debug((
                "Workfiles for launch context does not exists"
                " yet but path will be set."
            ))
        self.log.debug(
            "Setting last workfile path: {}".format(last_workfile_path)
        )

        self.launch_context.env["AVALON_LAST_WORKFILE"] = last_workfile_path
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

        project_settings = get_project_settings(project_name)['global']['tools']
        startup_presets = project_settings['Workfiles']['last_workfile_on_startup']

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
                for task_regex in self.compile_list_of_regexes(tasks_lowered):
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

    @staticmethod
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
