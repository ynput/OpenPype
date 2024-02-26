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
    global_default_attrs_values = load_openpype_default_settings()["project_settings"]["deadline"]\
                                    ["JobAttrsValues"]["DefaultValues"]
    deadline_attrs_names = ["pool", "pool_secondary", "priority", "limit_machine", "limits_plugin"]

    @classmethod
    def get_job_attr(cls, attr_name):
        if attr_name not in cls.deadline_attrs_names:
            # Attribute not found
            raise AttributeError("Unknown attribute {}".format(attr_name))

        if hasattr(cls, "_" + attr_name):
            # Attribute has been set, use it
            return getattr(cls, attr_name)

        try:
            # Value from project setting default values
            return get_current_project_settings()["deadline"]["JobAttrsValues"]["DefaultValues"][attr_name]
        except Exception: # noqa
            pass

        # Value from global setting default values
        return cls.global_default_attrs_values[attr_name]

    @classmethod
    def set_job_attr(cls, attr_name, value, ignore_error=False):
        if attr_name not in cls.deadline_attrs_names:
            # Attribute not found
            if ignore_error:
                return
            raise AttributeError("Unknown attribute {}".format(attr_name))

        setattr(cls, "_" + attr_name, value)

    @classmethod
    def set_job_attrs(cls, attrs_dict):
        for attr_name, value in attrs_dict.items():
            cls.set_job_attr(attr_name, value, ignore_error=True)


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

        # Ensure we return a dict (not None)
        if not profile:
            profile = {}

    return profile
