import bpy
import sys

import pyblish.api
import pyblish.util

from openpype.lib import version_up
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.workio import save_file, open_file


def update_data(workfile, source, collection_name, publish=True):
    """Update workfile data objects inside targeted collection from
    source blend file, save increment and publish if requested.
    """

    # Open work file.
    sys.stdout.write(f"Open workfile: {workfile}\n")
    try:
        result = open_file(workfile)
    except Exception:
        result = False
    if not result:
        sys.stderr.write("ERROR: Open workfile failed !\n")
        sys.exit(10)

    # Rename temporary all scene objects.
    for obj in bpy.data.objects:
        obj.name = f"{obj.name}.to_update"

    # Load only the collection wanted.
    sys.stdout.write(f"Load libraries from source: {source}\n")
    try:
        with bpy.data.libraries.load(
            source, link=False, relative=False
        ) as (data_from, data_to):
            for collection in data_from.collections:
                if collection == collection_name:
                    sys.stdout.write(f"load collection: {collection}\n")
                    data_to.collections.append(collection)
    except Exception:
        sys.stderr.write("ERROR: Load libraries failed !\n")
        sys.exit(11)

    # Reassign meshes from new data.
    for collection in data_to.collections:
        for obj in collection.all_objects:
            to_update = bpy.data.objects.get(f"{obj.name}.to_update")
            if to_update and to_update.data:
                # rename data
                original_data_name = to_update.data.name
                to_update.data.name = f"{to_update.data.name}.old"
                # copy new data and restor original name
                to_update.data = obj.data.copy()
                to_update.data.name = original_data_name
                sys.stdout.write(f"Data updated for: {obj.name}\n")
        plugin.remove_container(collection)

    plugin.orphans_purge()

    # Restor name for all scene objects
    for obj in bpy.data.objects:
        if obj.name.endswith(".to_update"):
            obj.name = obj.name[:-10]

    # Save new work version
    new_version = version_up(workfile)
    sys.stdout.write(f"Save new version: {new_version}\n")
    result = save_file(new_version, copy=False)
    if not result:
        sys.stderr.write("ERROR: Save new version failed !\n")
        sys.exit(20)

    # Publish
    if publish:
        sys.stdout.write("Publishing ..\n")
        result = pyblish.util.publish()
        sys.stdout.write(f"Publish result: {result}\n")
        if not result:
            sys.stderr.write("ERROR: Publish failed !\n")
            sys.exit(30)
    # Quit blender
    bpy.ops.wm.quit_blender()


if __name__ == "__main__":
    index = sys.argv.index("--")
    dest_workfile = sys.argv[index + 1]
    source_workfile = sys.argv[index + 2]
    collection_name = sys.argv[index + 3]
    publish = "--publish" in sys.argv

    update_data(dest_workfile, source_workfile, collection_name, publish)
