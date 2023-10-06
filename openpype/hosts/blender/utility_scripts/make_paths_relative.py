"""Make all paths relative."""

from pathlib import Path
import sys
import traceback

import bpy

from openpype.hosts.blender.api.utils import get_datablocks_with_filepath
from openpype.client.entities import get_representations
from openpype.pipeline.context_tools import (
    get_current_project_name,
    get_current_asset_name,
    get_current_task_name,
    get_workdir_from_session,
)
from openpype.lib.log import Logger

if __name__ == "__main__":
    log = Logger().get_logger()
    log.debug(
        f"Blend file | All paths converted to relative: {bpy.data.filepath}"
    )
    errors = []

    workfile_repre = max(
        filter(
            lambda r: r["context"].get("version") is not None,
            list(get_representations(
                get_current_project_name(),
                context_filters={
                    "asset": get_current_asset_name(),
                    "family": "workfile",
                    "task": {"name": get_current_task_name()},
                },
            ))
        ),
        key=lambda r: r["context"]["version"],
    )
    workdir = get_workdir_from_session()

    # Resolve path from source filepath with the relative filepath
    for datablock in get_datablocks_with_filepath(relative=False):
        # skip render result, compositing and generated images
        if (
            isinstance(datablock, bpy.types.Image)
            and datablock.source in {"GENERATED", "VIEWER"}
        ):
            continue
        try:
            datablock_filename = Path(datablock.filepath).name
            for file in workfile_repre.get("files"):
                if Path(file.get("path", "")).name == datablock_filename:
                    datablock.filepath = bpy.path.relpath(
                        str(
                            Path(
                                workdir, "resources", Path(
                                    datablock.filepath
                                ).name
                            )
                        ),
                        start=workdir,
                    )
                    break
            else:
                datablock.filepath = bpy.path.relpath(
                    str(Path(datablock.filepath).resolve()),
                    start=str(Path(bpy.data.filepath).parent.resolve()),
                )
        except BaseException as e:
            errors.append(sys.exc_info())

    try:
        bpy.ops.file.make_paths_relative()
    except BaseException as e:
        errors.append(sys.exc_info())

    bpy.ops.wm.save_mainfile()

    # Raise errors
    for e in errors:
        # Print syntax same as raising an exception
        traceback.print_exception(*e, file=sys.stdout)
