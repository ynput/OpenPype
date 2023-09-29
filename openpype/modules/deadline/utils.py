import os
import re
from openpype.settings import get_current_project_settings


def set_batch_name(instance, filename):
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
        "ext": ext[1:]
    }

    batch_name_settings = get_current_project_settings()["deadline"]["deadline_job_name"]  # noqa
    batch_name = batch_name_settings.format(**formatting_data)

    for m in re.finditer("__", batch_name):
        batch_name_list = list(batch_name)
        batch_name_list.pop(m.start())
        batch_name = "".join(batch_name_list)

    return batch_name
