import os
import bpy
import platform
from openpype.hosts.blender.api.workio import save_file
import pyblish.api
from avalon import io
import pyblish.util
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


def extract(file_to_open, filepath, collection_name):
    with bpy.data.libraries.load(file_to_open, link=False, relative=False) as (
        data_from,
        data_to,
    ):

        for data_from_collection in data_from.collections:
            if data_from_collection == collection_name:
                data_to.collections.append(data_from_collection)

    # Define extract output file path
    collection = bpy.data.collections.get(collection_name)
    bpy.context.scene.collection.children.link(collection)
    bpy.ops.object.make_local(type="ALL")
    bpy.data.orphans_purge(
        do_recursive=True, do_local_ids=True, do_linked_ids=True
    )

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
    collection[AVALON_PROPERTY] = data
    bpy.ops.object.make_local(type="ALL")
    bpy.data.orphans_purge(
        do_recursive=True, do_local_ids=True, do_linked_ids=True
    )
    save_file(filepath, copy=False)
    print("save")
    pyblish.util.publish()
    print("pulish")


import sys

argv = sys.argv
argv = argv[argv.index("--") + 1 :]
file_to_open = argv[0]
filepath = argv[1]
collection_name = argv[2]
extract(file_to_open, filepath, collection_name)
print(argv)
