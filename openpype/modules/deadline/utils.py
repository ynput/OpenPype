import os
import re

from openpype.lib import filter_profiles
from openpype.pipeline.context_tools import (
    _get_modules_manager,
    get_current_task_name
)
from openpype.settings.lib import load_openpype_default_settings
from openpype.settings import get_current_project_settings

class RecalculateOnAccess:
    def __init__(self, fget):
        self.fget = fget

    def __get__(self, instance, owner):
        return self.fget(instance)

class DeadlineDefaultJobAttrs:
    deadline_job_attrs_global_settings = load_openpype_default_settings()['project_settings']['deadline']['JobAttrsValues']
    _pool = deadline_job_attrs_global_settings['DefaultValues']['pool']
    _pool_secondary = deadline_job_attrs_global_settings['DefaultValues']['pool_secondary']
    _priority = deadline_job_attrs_global_settings['DefaultValues']['priority']
    _limit_machine = deadline_job_attrs_global_settings['DefaultValues']['limit_machine']
    _limits_plugin = deadline_job_attrs_global_settings['DefaultValues']['limits_plugin']

    @RecalculateOnAccess
    def pool(self):
        return (get_current_project_settings()['deadline']['JobAttrsValues']['DefaultValues']['pool']
                or self._pool)

    @RecalculateOnAccess
    def pool_secondary(self):
        return (get_current_project_settings()['deadline']['JobAttrsValues']['DefaultValues']['pool_secondary']
                or self._pool_secondary)

    @RecalculateOnAccess
    def priority(self):
        return (get_current_project_settings()['deadline']['JobAttrsValues']['DefaultValues']['priority']
                or self._priority)

    @RecalculateOnAccess
    def limit_machine(self):
        return (get_current_project_settings()['deadline']['JobAttrsValues']['DefaultValues']['limit_machine']
                or self._limit_machine)

    @RecalculateOnAccess
    def limits_plugin(self):
        return (get_current_project_settings()['deadline']['JobAttrsValues']['DefaultValues']['limits_plugin']
                or self._limits_plugin)


class SafeDict(dict):
    def __missing__(self, key):
        return '{' + key + '}'


def set_custom_deadline_name(instance, filename, setting):
    context = instance.context
    basename, ext = os.path.splitext(filename)
    version = "v" + str(instance.data.get("version")).zfill(3)
    subversion = basename.split("_")[-1]
    if re.match(r'^v[0-9]+$', subversion):
        # If the last part of the filename is the version,
        # this means there is no subversion (a.k.a comment).
        # Lets clear the variable
        subversion = ""

    anatomy_data = context.data.get("anatomyData")

    formatting_data = {
        "workfile": basename,
        "asset": anatomy_data.get("asset"),
        "task": anatomy_data.get("task"),
        "subset": instance.data.get("subset"),
        "version": version,
        "project": anatomy_data.get("project"),
        "family": instance.data.get("family"),
        "comment": instance.data.get("comment"),
        "subversion": subversion,
        "inst_name": instance.data.get("name"),
        "ext": ext[1:]
    }

    custom_name_settings = get_current_project_settings()["deadline"][setting]  # noqa
    try:
        custom_name = custom_name_settings.format_map(
            SafeDict(**formatting_data)
        )

        for m in re.finditer("__", custom_name):
            custom_name_list = list(custom_name)
            custom_name_list.pop(m.start())
            custom_name = "".join(custom_name_list)

        if custom_name.endswith("_"):
            custom_name = custom_name[:-1]
    except Exception as e:
        raise KeyError(
            "OpenPype Studio Settings (Deadline section): Syntax issue(s) "
            "in \"Job Name\" or \"Batch Name\" for the current project.\n"
            "Error: {}".format(e)
        )

    return custom_name


def get_deadline_limits_plugin(deadline_enabled, deadline_url, log):
    manager = _get_modules_manager()
    deadline_module = manager.modules_by_name["deadline"]

    limits_plugin = []
    if deadline_enabled and deadline_url:
        requested_arguments = {"NamesOnly": True}
        limits_plugin = deadline_module.get_deadline_data(
            deadline_url,
            "limitgroups",
            log=log,
            **requested_arguments
        )

    return limits_plugin


def get_deadline_job_profile(project_settings, host):
    settings = project_settings["deadline"]["JobAttrsValues"] # noqa
    task = get_current_task_name()
    profile = {}

    filtering_criteria = {
        "hosts": host,
        "task_types": task
    }

    if settings.get("profiles"):
        profile = filter_profiles(settings["profiles"], filtering_criteria)

    return profile
