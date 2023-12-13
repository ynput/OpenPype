import os
from openpype.lib import Logger
import pyblish.api
import pyblish.util

from openpype.hosts.traypublisher.api import TrayPublisherHost
from openpype.pipeline import register_host
from openpype.lib.attribute_definitions import FileDefItem
from openpype.pipeline.create import CreateContext


from pprint import pformat

def csvpublish(
    csv_filepath,
    project_name,
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
    os.environ["AVALON_PROJECT"] = project_name

    host = TrayPublisherHost()
    register_host(host)

    # create context and loop trough all csv creator

    # will need to create publish context
    # in publish context in context.data `create_context`

    file_field = FileDefItem.from_paths([csv_filepath], False).pop().to_dict()
    print(f"file_field: {file_field}")

    precreate_data = {
        "file": file_field,
        "project": project_name
    }
    create_context = CreateContext(host)
    create_context.create(
        "creator.identifier",
        variant,
        asset_doc,
        task_name,
        precreate_data
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
