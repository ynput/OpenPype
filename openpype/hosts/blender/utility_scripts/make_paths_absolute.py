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

    current_filepath = Path(bpy.data.filepath)
    if args.source_filepath:
        for lib in bpy.data.libraries:
            lib.filepath = str(Path(bpy.path.abspath(lib.filepath, start=args.source_filepath.parent)).resolve())
            try:
                lib.reload()
            except RuntimeError as e:
                log.error(e)
    else:
        bpy.ops.file.make_paths_absolute()

    bpy.ops.wm.save_mainfile()
