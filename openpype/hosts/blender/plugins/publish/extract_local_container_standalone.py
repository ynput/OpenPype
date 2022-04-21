import bpy
import sys

from openpype.hosts.blender.api.workio import save_file
import pyblish.api
from avalon import io
import pyblish.util
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY
from openpype.hosts.blender.api import plugin


def clean_scene():
    """Remove the data_blocks without users"""
    for object in bpy.data.objects:
        bpy.data.objects.remove(object)
    for collection in bpy.data.collections:
        bpy.data.collections.remove(collection)
    plugin.remove_orphan_datablocks()


def extract(file_to_open, filepath, collection_name):
    """
    Extract a container if some parts are local,
    save a work file And publish
    """

    with bpy.data.libraries.load(file_to_open, link=False, relative=False) as (
        data_from,
        data_to,
    ):
        # Load only the collection wanted
        for data_from_collection in data_from.collections:
            if data_from_collection == collection_name:
                data_to.collections.append(data_from_collection)
    # Get the collection from data
    container = bpy.data.collections.get(collection_name)
    # And link them to the scene colection
    bpy.context.scene.collection.children.link(container)
    bpy.ops.object.make_local(type="ALL")
    plugin.remove_orphan_datablocks()
    plugin.remove_namespace_for_objects_container(container)

    objects = plugin.get_all_objects_in_collection(container)

    # Find the modifiers with armature data to remove them
    for object in objects:
        if object.animation_data:
            if object.animation_data.drivers:
                drivers = object.animation_data.drivers
                modifier_to_delete = []
                for driver in drivers:
                    if driver is not None:
                        data_path = driver.data_path
                        variables = driver.driver.variables
                        for variable in variables:
                            if variable is not None:
                                targets = variable.targets
                                for target in targets:
                                    if target is not None:
                                        target_id = target.id
                                        if target_id is not None:
                                            if target_id.type == "ARMATURE":
                                                modifier_data_path = (
                                                    data_path.split(".")[0]
                                                )
                                                try:
                                                    modifier = (
                                                        object.path_resolve(
                                                            modifier_data_path,
                                                            False,
                                                        )
                                                    )
                                                    object.animation_data.drivers.remove(
                                                        driver
                                                    )
                                                    if "modifier" in data_path:

                                                        if (
                                                            modifier
                                                            not in modifier_to_delete
                                                        ):
                                                            modifier_to_delete.append(
                                                                modifier
                                                            )
                                                except Exception as inst:
                                                    print(inst)

                for modifier in modifier_to_delete:
                    object.modifiers.remove(modifier)
        object.animation_data_clear()
    # Delete the modifiers
    objects = plugin.get_all_objects_in_collection(container)
    for object in objects:
        for modifier in object.modifiers:
            if modifier.type == "ARMATURE":
                object.modifiers.remove(modifier)

    plugin.remove_orphan_datablocks()

    # Get container data from the data base
    representation = io.find_one(
        {"_id": io.ObjectId(container[AVALON_PROPERTY]["representation"])}
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
    container[AVALON_PROPERTY] = data
    bpy.ops.object.make_local(type="ALL")
    plugin.remove_orphan_datablocks()

    # Save a work version
    save_file(filepath, copy=False)
    # Publish
    pyblish.util.publish()
    # Quit blender
    bpy.ops.wm.quit_blender()


if __name__ == "__main__":
    argv = sys.argv
    argv = argv[argv.index("--") + 1 :]
    file_to_open = argv[0]
    filepath = argv[1]
    collection_name = argv[2]
    clean_scene()
    extract(file_to_open, filepath, collection_name)
