import re
from typing import List

import bpy
from bpy.app.handlers import persistent

from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY
from openpype.pipeline import install_host
from openpype.hosts.blender import api
from openpype.pipeline.constants import AVALON_CONTAINER_ID, AVALON_INSTANCE_ID
from openpype.pipeline.load.plugins import (
    LoaderPlugin,
    discover_loader_plugins,
)
from openpype.pipeline.load.utils import loaders_from_repre_context

camel_case_first = re.compile(r"^[A-Z][a-z]*")

all_loaders = discover_loader_plugins()


def get_loader_name(loaders: List[LoaderPlugin], load_type: str) -> str:
    """Get loader name from list by requested load type.

    Args:
        loaders (List[LoaderPlugin]): List of available loaders
        load_type (str): Load type to get loader of

    Returns:
        str: Loader name
    """
    return next(
        (l.__name__ for l in loaders if l.__name__.startswith(load_type)),
        None,
    )


@persistent
def loader_attribution_handler(_):
    """Handler to attribute loader name to containers loaded outside of OP.

    For example if you link a container using Blender's file tools.
    """
    # Get all types
    all_types = [
        getattr(bpy.data, datablock)
        for datablock in dir(bpy.data)
        if not datablock.startswith("__")
    ]
    all_instanced_collections = {
        obj.instance_collection
        for obj in bpy.context.scene.objects
        if obj.is_instancer and obj.instance_collection.library
    }
    for bl_type in all_types:
        # Filter type for only collections (and not functions)
        if isinstance(bl_type, bpy.types.bpy_prop_collection) and len(bl_type):
            for datablock in bl_type:
                avalon_data = datablock.get(AVALON_PROPERTY)
                if (
                    not avalon_data
                    or avalon_data.get("id") == AVALON_INSTANCE_ID
                ):
                    continue

                # Get available loaders
                all_loaders = discover_loader_plugins()
                context = {
                    "subset": {"schema": AVALON_CONTAINER_ID},
                    "version": {"data": {"families": [avalon_data["family"]]}},
                    "representation": {"name": "blend"},
                }
                loaders = loaders_from_repre_context(all_loaders, context)

                # Instance loader, an instance in OP is necessarily a link
                if (
                    type(datablock) is bpy.types.Collection
                    and datablock in all_instanced_collections
                ):
                    datablock[AVALON_PROPERTY]["loader"] = get_loader_name(
                        loaders, "Instance"
                    )
                else:
                    if datablock.library:  # Link loader
                        datablock[AVALON_PROPERTY]["loader"] = get_loader_name(
                            loaders, "Link"
                        )
                    else:  # Append loader
                        datablock[AVALON_PROPERTY]["loader"] = get_loader_name(
                            loaders, "Append"
                        )


@persistent
def instances_purge_handler(_):
    """Remove instances for which all datablocks have been removed."""
    scene = bpy.context.scene
    if not hasattr(scene, "openpype_instances"):
        return
    
    for op_instance in scene.openpype_instances:
        if not any({d_ref.datablock for d_ref in op_instance.datablock_refs}):
            scene.openpype_instances.remove(
                scene.openpype_instances.find(op_instance.name)
            )
            continue


def register():
    bpy.app.handlers.save_pre.append(loader_attribution_handler)
    bpy.app.handlers.save_pre.append(instances_purge_handler)

    install_host(api)


def unregister():
    pass
