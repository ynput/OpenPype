import os
import bpy
import platform

from avalon import io
import openpype.api
from openpype.lib import version_up
from openpype.hosts.blender.api.workio import save_file
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY
from openpype.hosts.blender.api.plugin import is_local_collection


def extract(file_to_open,filepath, collection_name):
    bpy.ops.wm.open_mainfile(filepath=file_to_open)
    # Define extract output file path

    # Get the main scene
    scene = bpy.data.scenes["Scene"]

    collection_to_extract = bpy.data.collections[collection_name]
    # Get all the collection of the container. The farest parents in first for override them first
    collections = []
    nodes = list(bpy.scene.collection.children)

    for collection in nodes:
        if collection != collection_to_extract:
            collections.append(collection)
            nodes.extend(list(collection.children))

    # Get all the object of the container. The farest parents in first for override them first
    objects = []

    for collection in collections:
        nodes = list(collection.objects)
        objects_of_the_collection = []
        for obj in nodes:
            if obj.parent is None:
                objects_of_the_collection.append(obj)
        nodes = objects_of_the_collection

        for obj in nodes:
            objects.append(obj)
            nodes.extend(list(obj.children))
        objects.reverse()
    print(objects)

import sys
argv = sys.argv
argv = argv[argv.index("--") + 1 :]  # get all args after "--"
filepath = argv[0]
collection_name = argv[1]
extract(file_to_open,filepath, collection_name)
print(argv)  # --> ['example', 'args', '123']
