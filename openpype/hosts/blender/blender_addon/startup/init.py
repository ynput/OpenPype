import re

import bpy
from bpy.app.handlers import persistent

from openpype.hosts.blender.api.utils import assign_loader_to_datablocks
from openpype.pipeline import install_host
from openpype.hosts.blender import api
from openpype.pipeline.load.plugins import (
    discover_loader_plugins,
)

camel_case_first = re.compile(r"^[A-Z][a-z]*")

all_loaders = discover_loader_plugins()


@persistent
def loader_attribution_handler(*args):
    """Handler to attribute loader name to containers loaded outside of OP.

    For example if you link a container using Blender's file tools.
    """
    assign_loader_to_datablocks(
        [
            d
            for d in (
                bl_type
                for bl_type in dir(bpy.data)
                if not bl_type.startswith("__")
                and isinstance(bl_type, bpy.types.bpy_prop_collection)
                and len(bl_type)
            )
        ]
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
