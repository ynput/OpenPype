import os
import re

from openpype.settings import get_current_project_settings


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
