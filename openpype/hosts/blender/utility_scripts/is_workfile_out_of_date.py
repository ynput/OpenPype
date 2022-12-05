from pathlib import Path
from datetime import datetime

from openpype.lib.dateutils import get_timestamp
from openpype.client.entities import get_last_version_by_subset_name
from openpype.pipeline import legacy_io
from openpype.hosts.blender.api.workio import current_file


def is_work_file_out_of_date() -> bool:
    """Check if the current workfile is out of date.
    This is based on last modification date, so if a user modifies an out of
    date workfile, this will return `False`. Also, in case of partial publish,
    this will return `True`.

    Returns:
        bool: True if the current workfile is out of date.
    """

    session = legacy_io.Session

    # Getting date and time of the latest published workfile
    last_published_time = get_last_version_by_subset_name(
        legacy_io.active_project(),
        f"workfile{session.get('AVALON_TASK')}",
        asset_name=session.get("AVALON_ASSET"),
    )["data"]["time"]

    # Getting date and time of the latest locally installed workfile
    # Time is converted to use the same format as for `last_publishd_time`
    workfile_time = get_timestamp(
        datetime.fromtimestamp(Path(current_file()).stat().st_mtime)
    )

    return last_published_time > workfile_time
