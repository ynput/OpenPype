import bpy
from openpype.hosts.blender.api.workio import save_file
import pyblish.api
from avalon import io
import pyblish.util
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY
from openpype.hosts.blender.api import plugin


def extract(file_to_open, filepath, collection_name):
    """Extract a container if some parts are local save a work file And publish"""
    with bpy.data.libraries.load(file_to_open, link=False, relative=False) as (
        data_from,
        data_to,
    ):
        # Load only the collection wanted
        for data_from_collection in data_from.collections:
            if data_from_collection == collection_name:
                data_to.collections.append(data_from_collection)
    # Get the collection from data
    collection = bpy.data.collections.get(collection_name)
    # And link them to the scene colection
    bpy.context.scene.collection.children.link(collection)
    bpy.ops.object.make_local(type="ALL")

    objects_list = plugin.get_all_objects_in_collection(collection)
    for object in objects_list:
        if object.animation_data:
            if object.animation_data.drivers:
                drivers = object.animation_data.drivers
                modifier_to_delete = []
                for driver in drivers:
                    data_path = driver.data_path
                    variables = driver.driver.variables
                    for variable in variables:
                        targets = variable.targets
                        for target in targets:
                            target_id = target.id
                            if target_id.type == "ARMATURE":
                                modifier_data_path = data_path.split(".")[0]
                                try:
                                    modifier = object.path_resolve(
                                        modifier_data_path, False
                                    )
                                    object.animation_data.drivers.remove(
                                        driver
                                    )
                                    if "modifier" in data_path:

                                        if modifier not in modifier_to_delete:
                                            modifier_to_delete.append(modifier)
                                except:
                                    print(
                                        f" '{modifier_data_path}' could not be resolved"
                                    )
                for modifier in modifier_to_delete:
                    object.modifiers.remove(modifier)
        object.animation_data_clear()

    objects_List = plugin.get_all_objects_in_collection(collection)
    for object in objects_List:
        for modifier in object.modifiers:
            if modifier.type == "ARMATURE":
                object.modifiers.remove(modifier)

    plugin.remove_orphan_datablocks()

    # Get container data from the data base
    representation = io.find_one(
        {"_id": io.ObjectId(collection[AVALON_PROPERTY]["representation"])}
    )

    family = representation["context"]["family"]
    asset = representation["context"]["asset"]
    subset = representation["context"]["subset"]
    variant = subset.replace(family, "")
    task = representation["context"]["task"]["name"]

    data = {
        "id": "pyblish.avalon.instance",
        "family": family,
        "asset": asset,
        "subset": subset,
        "active": 1,
        "variant": variant,
        "task": task,
    }
    # Store the data in the avalon custom property
    collection[AVALON_PROPERTY] = data
    bpy.ops.object.make_local(type="ALL")
    plugin.remove_orphan_datablocks()

    # Save a work version
    save_file(filepath, copy=False)
    # Publish
    pyblish.util.publish()
    # Quit blender
    bpy.ops.wm.quit_blender()


import sys

if __name__ == "__main__":
    argv = sys.argv
    argv = argv[argv.index("--") + 1 :]
    file_to_open = argv[0]
    filepath = argv[1]
    collection_name = argv[2]
    extract(file_to_open, filepath, collection_name)
