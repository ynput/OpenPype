"""Blender properties."""

from typing import Iterable, Set, Union
import bpy
from bpy.types import PropertyGroup
from bpy.utils import register_classes_factory

from openpype.hosts.blender.api.utils import (
    BL_OUTLINER_TYPES,
    get_root_datablocks,
)


def get_datablock_name(self) -> str:
    """Get name, ensure to be identical to the referenced datablock's name.

    Returns:
        str: Name
    """
    if self.datablock and self.datablock.name != self.get("name"):
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
    """A datablock reference is a direct link to a datblock.

    To access the actual datablock, use `d_ref.datablock`.
    Its name is exactly the same as the datablock's, even though it changes.
    """

    name: bpy.props.StringProperty(
        name="OpenPype Instance name",
        get=get_datablock_name,
        set=set_datablock_name,
    )
    datablock: bpy.props.PointerProperty(
        name="Datablock reference", type=bpy.types.ID
    )
    keep_fake_user: bpy.props.BoolProperty(
        name="Keep fake user",
        description="In case it was fake user before being put into instance",
    )


class OpenpypeGroup(PropertyGroup):
    datablock_refs: bpy.props.CollectionProperty(
        name="OpenPype Datablocks references",
        type=OpenpypeDatablockRef,
    )

    def get_datablocks(
        self,
        types: Union[bpy.types.ID, Iterable[bpy.types.ID]] = None,
        only_local=True,
    ) -> Set[bpy.types.ID]:
        """Get all the datablocks referenced by this container.

        Types can be filtered.

        Args:
            types (Iterable): List of types to filter the datablocks

        Returns:
            set: Set of datablocks
        """
        # Put into iterable if not
        if types is not None and not isinstance(types, Iterable):
            types = (types,)

        return {
            d_ref.datablock
            for d_ref in self.datablock_refs
            if d_ref
            and d_ref.datablock
            and (not only_local or not d_ref.datablock.library)
            and (types is None or isinstance(d_ref.datablock, tuple(types)))
        }

    def get_root_datablocks(
        self, types: Union[bpy.types.ID, Iterable[bpy.types.ID]] = None
    ) -> Set[bpy.types.ID]:
        """Get the root datablocks of the container.

        A root datablock is the first datablock of the hierarchy that is not
        referenced by another datablock in the container.

        Args:
            types (Iterable): List of types to filter the datablocks

        Returns:
            bpy.types.ID: Root datablock
        """
        return get_root_datablocks(self.get_datablocks(types))

    def get_root_outliner_datablocks(self) -> Set[bpy.types.ID]:
        """Get the root outliner datablocks of the container.

        A root datablock is the first datablock of the hierarchy that is not
        referenced by another datablock in the container.

        Returns:
            bpy.types.ID: Root datablock
        """
        return self.get_root_datablocks(BL_OUTLINER_TYPES)


class OpenpypeInstance(OpenpypeGroup):
    """An instance references datablocks to be published.

    The list is exhaustive unless it relates to outliner datablocks,
    such as objects or collections. In this case it references only the first
    entity of the hierarchy (collection or object with all children) to allow
    the user to handle the instance contents with the outliner.
    """

    name: bpy.props.StringProperty(name="OpenPype Instance name")
    datablock_active_index: bpy.props.IntProperty(
        name="Datablock Active Index"
    )
    publish: bpy.props.BoolProperty(
        name="Publish",
        description="Is instance selected for publish",
        default=True,
    )

    # = Custom properties =
    # "icons" (List): List of the icons names for the authorized types


class OpenpypeContainer(OpenpypeGroup):
    """A container references all the loaded datablocks.

    In case the container references an outliner entity (collection or object)
    its name is constantly the same as this entity, even though it may change.
    """

    name: bpy.props.StringProperty(
        name="OpenPype Container name",
    )
    datablock_refs: bpy.props.CollectionProperty(
        name="OpenPype Container Datablocks references",
        type=OpenpypeDatablockRef,
    )
    library: bpy.props.PointerProperty(
        name="OpenPype Container source library", type=bpy.types.Library
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
    bpy.types.WindowManager.openpype_containers = bpy.props.CollectionProperty(
        name="OpenPype Containers", type=OpenpypeContainer, options={"HIDDEN"}
    )


def unregister():
    """Unregister the properties."""
    factory_unregister()

    del bpy.types.Scene.openpype_instances
    del bpy.types.Scene.openpype_instance_active_index

    del bpy.types.window_manager.openpype_containers
