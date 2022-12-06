"""Blender properties."""

import bpy
from bpy.types import PropertyGroup
from bpy.utils import register_classes_factory


class OpenpypeInstanceDatablockRef(PropertyGroup):
    name: bpy.props.StringProperty(name="OpenPype Instance name")
    datapath: bpy.props.StringProperty(name="OpenPype Instance name")

    # = Custom properties =
    # "outliner_entity" Union[bpy.types.Collection, bpy.types.Object]:
    #       Entity in outliner if outliner datablock


class OpenpypeInstance(PropertyGroup):
    name: bpy.props.StringProperty(name="OpenPype Instance name")
    datablocks: bpy.props.CollectionProperty(
        name="OpenPype Instance Datablocks references", type=OpenpypeInstanceDatablockRef
    )
    datablock_active_index: bpy.props.IntProperty(
        name="Datablock Active Index"
    )

    # = Custom properties =
    # "icons" (List): List of the icons names for the authorized types


class OpenpypeContainer(PropertyGroup):
    name: bpy.props.StringProperty(name="OpenPype Container name")
    datablocks: bpy.props.CollectionProperty(
        name="OpenPype Container Datablocks references", type=OpenpypeInstanceDatablockRef
    )


classes = [
    OpenpypeInstanceDatablockRef,
    OpenpypeInstance,
    OpenpypeContainer,
]


factory_register, factory_unregister = register_classes_factory(classes)


def register():
    "Register the properties."
    factory_register()

    bpy.types.Scene.openpype_instances = bpy.props.CollectionProperty(
        name="OpenPype Instances", type=OpenpypeInstance, options={"HIDDEN"}
    )
    bpy.types.Scene.openpype_instance_active_index = bpy.props.IntProperty(
        name="OpenPype Instance Active Index", options={"HIDDEN"}
    )
    bpy.types.Collection.is_openpype_instance = bpy.props.BoolProperty()
    
    bpy.types.Scene.openpype_containers = bpy.props.CollectionProperty(
        name="OpenPype Containers", type=OpenpypeContainer, options={"HIDDEN"}
    )


def unregister():
    """Unregister the properties."""
    factory_unregister()

    del bpy.types.Scene.openpype_instances
    del bpy.types.Scene.openpype_instance_active_index
    del bpy.types.Collection.is_openpype_instance
    
    del bpy.types.Scene.openpype_containers
