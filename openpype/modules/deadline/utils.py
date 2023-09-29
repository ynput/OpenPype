from openpype.settings import get_current_project_settings


def set_batch_name(instance, filename):
    context = instance.context
    subversion = filename.split("_")[-1].split(".")[0]
    anatomy_data = context.data.get("anatomyData")

    formatting_data = {
        "asset": anatomy_data.get("asset"),
        "task": anatomy_data.get("task"),
        "subset": instance.data.get("subset"),
        "version": "v" + str(instance.data.get("version")).zfill(3),
        "project": anatomy_data.get("project"),
        "family": instance.data.get("family"),
        "comment": instance.data.get("comment"),
        "subversion": subversion or '',
        "ext": "ma"
    }

    batch_name_settings = get_current_project_settings()["deadline"]["deadline_job_name"]  # noqa
    batch_name = batch_name_settings.format(**formatting_data)

    return batch_name
