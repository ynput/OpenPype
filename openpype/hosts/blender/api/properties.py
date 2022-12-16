"""Blender properties."""

import bpy
from bpy.types import PropertyGroup
from bpy.utils import register_classes_factory


def get_datablock_name(self) -> str:
    """Get name, ensure to be identical to the referenced datablock's name.

    Returns:
        str: Name
    """
    if self.datablock and self.datablock.name != self["name"]:
        self["name"] = self.datablock.name

    return self["name"]


def set_datablock_name(self, value: str):
    """Set name, ensure the referenced datablock to have the same.

    Args:
        value (str): Name
    """
    if self.datablock and self.datablock.name != self["name"]:
        self.datablock.name = value
    self["name"] = value


class OpenpypeDatablockRef(PropertyGroup):
    name: bpy.props.StringProperty(
        name="OpenPype Instance name",
        get=get_datablock_name,
        set=set_datablock_name,
    )
    datablock: bpy.props.PointerProperty(
        name="Datablock reference", type=bpy.types.ID
    )


class OpenpypeInstance(PropertyGroup):
    name: bpy.props.StringProperty(name="OpenPype Instance name")
    datablocks: bpy.props.CollectionProperty(
        name="OpenPype Instance Datablocks references",
        type=OpenpypeDatablockRef,
    )
    datablock_active_index: bpy.props.IntProperty(
        name="Datablock Active Index"
    )

    # = Custom properties =
    # "icons" (List): List of the icons names for the authorized types


def get_container_name(self) -> str:
    """Get name, apply it to the referenced outliner entity's name.

    Returns:
        str: Name
    """
    if self.outliner_entity and self.outliner_entity.name != self["name"]:
        self["name"] = self.outliner_entity.name

    return self["name"]


def set_container_name(self, value: str):
    """Set name, ensure the referenced outliner entity to have the same.

    Args:
        value (str): Name
    """
    if self.outliner_entity and self.outliner_entity.name != self["name"]:
        self.outliner_entity.name = value

    self["name"] = value


class OpenpypeContainer(PropertyGroup):
    name: bpy.props.StringProperty(
        name="OpenPype Container name",
        get=get_container_name,
        set=set_container_name,
    )
    datablocks: bpy.props.CollectionProperty(
        name="OpenPype Container Datablocks references",
        type=OpenpypeDatablockRef,
    )
    library: bpy.props.PointerProperty(
        name="OpenPype Container source library", type=bpy.types.Library
    )
    outliner_entity: bpy.props.PointerProperty(
        name="Outliner entity reference", type=bpy.types.ID
    )


classes = [
    OpenpypeDatablockRef,
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
