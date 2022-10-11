import re

import bpy
from bpy.app.handlers import persistent

from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY
from openpype.pipeline import install_host
from openpype.hosts.blender import api

camel_case_first = re.compile(r"^[A-Z][a-z]*")


@persistent
def load_handler(scene):
    # Get all types
    all_types = [
        getattr(bpy.data, datablock) for datablock in dir(bpy.data) if not datablock.startswith("__")
    ]
    all_instanced_collections = {
        obj.instance_collection
        for obj in scene.objects
        if obj.is_instancer and obj.instance_collection.library
    }
    for bl_type in all_types:
        # Filter type for only collections (and not functions)
        if isinstance(bl_type, bpy.types.bpy_prop_collection) and len(bl_type):
            for datablock in bl_type:
                avalon_data = datablock.get(AVALON_PROPERTY, {})
                loader_name = avalon_data.get("loader")
                if not avalon_data or not loader_name:
                    continue

                # Instance loader, an instance in OP is necessarily a link
                current_loading_type = camel_case_first.findall(loader_name)[0]
                if (
                    type(datablock) is bpy.types.Collection
                    and datablock in all_instanced_collections
                ):
                    datablock[AVALON_PROPERTY]["loader"] = loader_name.replace(
                        current_loading_type, "Instance"
                    )
                else:
                    if datablock.library:  # Link loader
                        datablock[AVALON_PROPERTY][
                            "loader"
                        ] = loader_name.replace(current_loading_type, "Link")
                    else:  # Append loader
                        datablock[AVALON_PROPERTY][
                            "loader"
                        ] = loader_name.replace(current_loading_type, "Append")


def register():
    bpy.app.handlers.depsgraph_update_pre.append(load_handler)

    install_host(api)


def unregister():
    pass
