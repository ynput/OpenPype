"""Make all paths absolute."""

import argparse
from pathlib import Path
import sys

import bpy

from openpype.lib.log import Logger

if __name__ == "__main__":
    log = Logger().get_logger()
    log.debug(
        f"Blend file | All paths converted to absolute: {bpy.data.filepath}"
    )

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Update AVALON metadata with given representation ID."
    )
    parser.add_argument(
        "--source_filepath",
        type=Path,
        nargs="?",
        help="source filepath",
    )
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])

    if args.source_filepath.is_file():
        # Resolve path from source filepath with the relative filepath
        datablocks_with_filepath = list(bpy.data.libraries) + list(
            bpy.data.images
        )
        for datablock in datablocks_with_filepath:
            try:
                if datablock and datablock.filepath.startswith("//"):
                    datablock.filepath = str(
                        Path(
                            bpy.path.abspath(
                                datablock.filepath,
                                start=args.source_filepath.parent,
                            )
                        ).resolve()
                    )
                    datablock.reload()
            except (RuntimeError, ReferenceError, OSError) as e:
                log.error(e)
    else:
        bpy.ops.file.make_paths_absolute()

    if bpy.data.filepath:
        bpy.ops.wm.save_mainfile()
