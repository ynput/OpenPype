"""Make all paths absolute."""

import argparse
from pathlib import Path
import sys

import bpy
from openpype.hosts.blender.api.utils import make_paths_absolute

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
        make_paths_absolute(args.source_filepath)

    if bpy.data.filepath:
        bpy.ops.wm.save_mainfile()
