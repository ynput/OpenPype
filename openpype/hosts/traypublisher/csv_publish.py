import pyblish.api
import pyblish.util

from openpype.hosts.traypublisher.api import TrayPublisherHost
from openpype.pipeline import install_host
from openpype.lib.attribute_definitions import FileDefItem
from openpype.pipeline.create import CreateContext
from openpype.client import get_asset_by_name


from pprint import pformat

def csvpublish(
    csv_filepath,
    project_name,
    asset_name,
    task_name=None,
    username=None,
    targets=None
):
    """Publish CSV file.

    Args:
        csv_filepath (str): Path to CSV file.
        project_name (str): Project name.
        username (Optional[str]): User name.
        hostname (Optional[str]): Host name.
        targets (Optional[list[str]]): List of targets.
        logger (Optional[Logger]): Logger instance.
    """

    host = TrayPublisherHost()
    install_host(host)

    host.set_project_name(project_name)

    file_field = FileDefItem.from_paths([csv_filepath], False).pop().to_dict()
    precreate_data = {
        "csv_filepath_data": file_field,
    }
    create_context = CreateContext(host, headless=True)

    asset_doc = get_asset_by_name(
        project_name,
        asset_name
    )

    create_context.create(
        "io.openpype.creators.traypublisher.csv_ingest",
        "Main",
        asset_doc=asset_doc,
        task_name=task_name,
        pre_create_data=precreate_data,
    )

    # if username is provided add it to create context
    pyblish_context = pyblish.api.Context()
    pyblish_context.data["create_context"] = create_context

    if username:
        pyblish_context.data["user"] = username

    if targets:
        for target in targets:
            print(f"setting target: {target}")
            pyblish.api.register_target(target)

    pyblish.util.publish(context=pyblish_context)
