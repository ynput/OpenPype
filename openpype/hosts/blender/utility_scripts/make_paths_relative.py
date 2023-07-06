"""Make all paths relative."""

from pathlib import Path
import sys
import traceback

import bpy

from openpype.hosts.blender.api.utils import get_datablocks_with_filepath
from openpype.lib.log import Logger

if __name__ == "__main__":
    log = Logger().get_logger()
    log.debug(
        f"Blend file | All paths converted to relative: {bpy.data.filepath}"
    )
    errors = []
    # Resolve path from source filepath with the relative filepath
    for datablock in get_datablocks_with_filepath(relative=False):
        # skip render result, compositing and generated images
        if (
            isinstance(datablock, bpy.types.Image)
            and datablock.source in {"GENERATED", "VIEWER"}
        ):
            continue
        try:
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
