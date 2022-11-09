"""Blender properties."""

import bpy
from bpy.types import PropertyGroup
from bpy.utils import register_classes_factory


class OpenpypeInstanceDatablockRef(PropertyGroup):
    name: bpy.props.StringProperty(name="OpenPype Instance name")
    datapath: bpy.props.StringProperty(name="OpenPype Instance name")


class OpenpypeInstance(PropertyGroup):
    name: bpy.props.StringProperty(name="OpenPype Instance name")
    datablocks: bpy.props.CollectionProperty(
        name="OpenPype Instance Datapaths", type=OpenpypeInstanceDatablockRef
    )
    datablock_active_index: bpy.props.IntProperty(
        name="Datablock Active Index"
    )

    # = Custom properties =
    # "icons" (List): List of the icons names for the authorized types


classes = [
    OpenpypeInstanceDatablockRef,
    OpenpypeInstance,
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


def unregister():
    """Unregister the properties."""
    factory_unregister()

    del bpy.types.Scene.openpype_instances
