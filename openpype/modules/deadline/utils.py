import os
import re

from openpype.settings import get_current_project_settings


class SafeDict(dict):
    def __missing__(self, key):
        return '{' + key + '}'


def set_custom_deadline_name(instance, filename, setting):
    context = instance.context
    basename, ext = os.path.splitext(filename)
    subversion = basename.split("_")[-1]
    version = "v" + str(instance.data.get("version")).zfill(3)

    if subversion == version:
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
    custom_name = custom_name_settings.format_map(SafeDict(**formatting_data))

    for m in re.finditer("__", custom_name):
        custom_name_list = list(custom_name)
        custom_name_list.pop(m.start())
        custom_name = "".join(custom_name_list)

    if custom_name.endswith("_"):
        custom_name = custom_name[:-1]

    return custom_name
