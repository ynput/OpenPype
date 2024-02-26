import os
import re

from openpype.lib import filter_profiles
from openpype.pipeline.publish import OpenPypePyblishPluginMixin
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
        if not instance:
            return self.fget
        return self.fget(instance)


class DeadlineDefaultJobAttrs:
    global_default_attrs_values = load_openpype_default_settings()['project_settings']['deadline']\
                                    ['JobAttrsValues']['DefaultValues']
    pool: str = ""
    pool_secondary: str = ""
    priority: int = 0
    limit_machine: int = 0
    limits_plugin: list = []

    def __init__(self):
        self.pool = self.default_pool
        self.pool_secondary = self.default_pool_secondary
        self.priority = self.default_priority
        self.limit_machine = self.default_limit_machine
        self.limits_plugin = self.default_limits_plugin

    @property
    def default_pool(self):
        try:
            value = get_current_project_settings()['deadline']['JobAttrsValues']['DefaultValues']['pool']
        except Exception: # noqa
            value = self.global_default_attrs_values["pool"]
        return value

    @property
    def default_pool_secondary(self):
        try:
            value = get_current_project_settings()['deadline']['JobAttrsValues']['DefaultValues']['pool_secondary']
        except Exception: # noqa
            value = self.global_default_attrs_values["pool_secondary"]
        return value

    @property
    def default_priority(self):
        try:
            value = get_current_project_settings()['deadline']['JobAttrsValues']['DefaultValues']['priority']
        except Exception: # noqa
            value = self.global_default_attrs_values["priority"]
        return value

    @property
    def default_limit_machine(self):
        try:
            value = get_current_project_settings()['deadline']['JobAttrsValues']['DefaultValues']['limit_machine']
        except Exception: # noqa
            value = self.global_default_attrs_values["limit_machine"]
        return value

    @property
    def default_limits_plugin(self):
        try:
            value = get_current_project_settings()['deadline']['JobAttrsValues']['DefaultValues']['limits_plugin']
        except Exception: # noqa
            value = self.global_default_attrs_values["limits_plugin"]
        return value

    @staticmethod
    def get_attr_value(plugin, instance, attr_name, fallback=None):
        attrs = instance.data.get("attributeValues", {})
        if attr_name in attrs:
            return attrs.get(attr_name)

        attrs = instance.data.get("creator_attributes", {})
        if attr_name in attrs:
            return attrs.get(attr_name)

        if attr_name in instance.data:
            return instance.data.get(attr_name)

        attrs = OpenPypePyblishPluginMixin.get_attr_values_from_data_for_plugin(plugin, instance.data)
        if attr_name in attrs:
            return attrs.get(attr_name)

        if hasattr(plugin, attr_name):
            return getattr(plugin, attr_name)

        return fallback


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
