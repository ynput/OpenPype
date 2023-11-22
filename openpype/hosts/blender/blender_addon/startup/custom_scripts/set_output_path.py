import sys
import bpy
import argparse
import logging


def execute():

    parser = argparse.ArgumentParser()
    parser.add_argument("--output-path", help="Default output path for render")
    args, unknown = parser.parse_known_args(
        sys.argv[sys.argv.index("--") + 1 :]
    )

    bpy.context.scene.render.filepath = args.output_path
    logging.info(f"Default render filepath has been set to {bpy.context.scene.render.filepath}")


execute()
