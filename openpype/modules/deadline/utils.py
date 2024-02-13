import os
import re

from openpype.lib import filter_profiles
from openpype.pipeline.context_tools import (
    _get_modules_manager,
    get_current_task_name
)
from openpype.settings.lib import load_openpype_default_settings
from openpype.settings import get_current_project_settings


class DeadlineDefaultJobAttrs:
    deadline_job_attrs_global_settings = load_openpype_default_settings()['project_settings']['deadline']['JobAttrsValues']
    pool = deadline_job_attrs_global_settings['DefaultValues']['pool']
    pool_secondary = deadline_job_attrs_global_settings['DefaultValues']['pool_secondary']
    priority = deadline_job_attrs_global_settings['DefaultValues']['priority']
    limit_machine = deadline_job_attrs_global_settings['DefaultValues']['limit_machine']
    limits_plugin = deadline_job_attrs_global_settings['DefaultValues']['limits_plugin']


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
    if deadline_enabled:
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
    profile = {} # TODO: This should return values from the DefaultValues

    filtering_criteria = {
        "hosts": host,
        "task_types": task
    }

    if settings.get("profiles"):
        profile = filter_profiles(settings["profiles"], filtering_criteria)

    return profile