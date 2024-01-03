import os

import pyblish.api
import pyblish.util

from openpype.client import get_asset_by_name
from openpype.lib.attribute_definitions import FileDefItem
from openpype.pipeline import install_host
from openpype.pipeline.create import CreateContext

from openpype.hosts.traypublisher.api import TrayPublisherHost


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
        asset_name (str): Asset name.
        task_name (Optional[str]): Task name.
        username (Optional[str]): User name.
        hostname (Optional[str]): Host name.
        targets (Optional[list[str]]): List of targets.
    """

    # initialization of host
    host = TrayPublisherHost()
    install_host(host)

    # setting host context into project
    host.set_project_name(project_name)

    # add asset context to environment
    # TODO: perhaps this can be done in a better way?
    os.environ.update({
        "AVALON_PROJECT": project_name,
        "AVALON_ASSET": asset_name,
        "AVALON_TASK": task_name
    })

    # form precreate data with field values
    file_field = FileDefItem.from_paths([csv_filepath], False).pop().to_dict()
    precreate_data = {
        "csv_filepath_data": file_field,
    }

    # create context initialization
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

    # publishing context initialization
    pyblish_context = pyblish.api.Context()
    pyblish_context.data["create_context"] = create_context

    # setting username and targets
    if username:
        pyblish_context.data["user"] = username

    # publishing
    pyblish.util.publish(context=pyblish_context, targets=targets)
