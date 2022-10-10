import argparse
import sys

import bpy


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Update AVALON metadata with given representation ID."
    )
    parser.add_argument(
        "representation_id",
        type=str,
        nargs="?",
        help="representation ID",
    )
    args = parser.parse_args(sys.argv[sys.argv.index("--") :])

    # Get all types
    all_types = [
        getattr(bpy.data, a) for a in dir(bpy.data) if not a.startswith("__")
    ]
    for bl_type in all_types:
        # Filter type for only collections (and not functions)
        if isinstance(bl_type, bpy.types.bpy_prop_collection) and len(bl_type):
            for datablock in bl_type:
                # If 'representation' is set to boolean True, set given ID
                if datablock.get("avalon", {}).get("representation") == True:
                    datablock["avalon"][
                        "representation"
                    ] = args.representation_id

    bpy.ops.wm.save_mainfile()
