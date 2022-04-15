"""Load a model asset in Blender."""

from pathlib import Path
from typing import Dict, List, Optional

import bpy

from avalon import api
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import (
    AVALON_PROPERTY,
    AVALON_CONTAINER_ID,
)


class modfier_description:
    """
    Store the type, name, type,  properties and object modified  of a modifier
    The class has a method to create a modifier with this description
    """

    @property
    def properties(self):
        return self._properties

    @property
    def object(self):
        return self._object_name

    def create_blender_modifier(self):
        """
        create the modifier with the index, properties and object
        properties
        """
        if bpy.data.objects.get(self._object_name):
            object = bpy.data.objects[self._object_name]
            if object:
                if object.modifiers.get(self._properties["name"]) is None:
                    modifier = object.modifiers.new(
                        self._properties["name"],
                        self._properties["type"],
                    )
                    for property_key in self._properties.keys():
                        if not (modifier.is_property_readonly(property_key)):
                            property_value = self._properties[property_key]
                            setattr(modifier, property_key, property_value)

    def __init__(self, modifier: bpy.types.Modifier):
        """Get the index, properties and object modified of the modifier"""
        self._object_name = str()
        self._properties = dict()
        for property in dir(modifier):
            # filter the property
            if property not in [
                "__doc__",
                "__module__",
                "__slots__",
                "bl_rna",
                "is_active",
                "is_override_data",
                "rna_type",
                "show_expanded",
                "show_in_editmode",
                "show_on_cage",
                "show_render",
                "show_viewport",
                "use_apply_on_spline",
                "use_bone_envelopes",
                "use_deform_preserve_volume",
                "use_multi_modifier",
                "use_vertex_groups",
            ]:
                self._properties[property] = getattr(modifier, property)
        self._object_name = modifier.id_data.name


class BlendModelLoader(plugin.AssetLoader):
    """Load models from a .blend file.

    Because they come from a .blend file we can simply link the collection that
    contains the model. There is no further need to 'containerise' it.
    """

    families = ["model"]
    representations = ["blend"]
    label = "Link Model"
    icon = "code-fork"
    color = "orange"

    def _copy_driver(self, from_fcurve, target_fcurve):
        """Copy the driver on from an fcurve to another"""
        new_driver = target_fcurve.driver
        driver_to_copy = from_fcurve.driver
        new_driver.type = driver_to_copy.type
        new_driver.expression = driver_to_copy.expression
        new_driver.use_self = driver_to_copy.use_self
        for variable_to_copy in driver_to_copy.variables:
            new_variable = new_driver.variables.new()
            new_variable.name = variable_to_copy.name
            new_variable.type = variable_to_copy.type
            for i, target in variable_to_copy.targets.items():
                new_variable.targets[i].id = target.id_data
            for i, target in variable_to_copy.targets.items():
                for property in dir(target):
                    try:
                        setattr(
                            new_variable.targets[i],
                            property,
                            getattr(target, property),
                        )
                    except Exception as inst:
                        print(inst)

    def _store_drivers_in_an_empty(self, container):
        """
        Get all the drivers in the container's objects and
        copy them on an empty
        """
        # Create the empty
        empty = bpy.data.objects.new("empty", None)
        # Get all the container's objects
        objects_list = plugin.get_all_objects_in_collection(container)
        # Create animation data on the empty
        empty.animation_data_create()
        # Add a fake user to the empty to keep him if we remove orphan data
        empty.use_fake_user = True

        for object in objects_list:
            if object:
                if object.animation_data:
                    # Get the drivers on the object
                    drivers = object.animation_data.drivers
                    for driver in drivers:
                        # Create a driver on the empty with the
                        # data_path = name of the object + data_path of
                        # the object driver
                        new_driver = empty.animation_data.drivers.new(
                            object.name + ":" + driver.data_path
                        )
                        self._copy_driver(driver, new_driver)
        return empty

    def _set_drivers_from_empty(self, empty):
        """
        Get all the drivers in an empty and
        copy them on the container's objects
        """
        # Get the drivers store in the empty
        drivers = empty.animation_data.drivers
        for driver in drivers:
            # Get the data path on the driver
            data_path_with_object_name = driver.data_path
            # Get the object name and the data path store in the data_path
            # Data_path = object name + empty driver data_path
            object_name = data_path_with_object_name.split(":")[0]
            data_path = data_path_with_object_name.split(":")[1]

            object = bpy.data.objects[object_name]
            if object.animation_data is None:
                object.animation_data_create()
            if object.animation_data.drivers.find(data_path) is None:
                new_driver = object.animation_data.drivers.new(data_path)
                self._copy_driver(driver, new_driver)
        bpy.data.objects.remove(empty)

    def _get_modifier_parameters(self, container):
        """Get all modifier parameters of the container's objects in a dict"""
        objects_list = plugin.get_all_objects_in_collection(container)
        object_names_list = [object.name for object in objects_list]
        modifier_list = list()
        # Find the modifier properties of an object
        for object_name in object_names_list:
            object = bpy.data.objects.get(object_name)
            if object:
                for modifier in object.modifiers:
                    if modifier:
                        modifier_description = modfier_description(modifier)
                        # Set the modifier properties of an object in a dict
                        modifier_list.append(modifier_description)
        return modifier_list

    def _set_modifiers(self, modifier_list):
        """Set all modifier parameters of the container's objects"""
        modifier_list.reverse()
        for modifier_description in modifier_list:
            if bpy.data.objects.get(modifier_description.object):
                modifier_description.create_blender_modifier()

        for modifier_description in modifier_list:
            if bpy.data.objects.get(modifier_description.object):
                object = bpy.data.objects[modifier_description.object]
                if object:
                    bpy.context.view_layer.objects.active = object
                    try:
                        bpy.ops.object.modifier_move_to_index(
                            modifier=modifier_description.properties["name"],
                            index=0,
                        )
                    except Exception as ex:
                        print(ex)

    def _remove(self, container):
        """Remove the container and used data"""
        plugin.remove_container(container)

    def _process(self, libpath, asset_name):
        """Load the blend library file"""
        with bpy.data.libraries.load(libpath, link=True, relative=False) as (
            data_from,
            data_to,
        ):
            data_to.collections = data_from.collections

        # Get the scene collection
        scene_collection = bpy.context.scene.collection

        # Find the loaded collection and set in variable container_collection
        container_collection = None

        # Get all the containers in the data
        containers = plugin.get_containers_list()

        # Get the container with the good asset name and the good family
        for container in containers:
            if container.override_library is None:
                if container[AVALON_PROPERTY].get("family"):
                    if container[AVALON_PROPERTY]["family"] == "model":
                        if container[AVALON_PROPERTY].get("asset_name"):
                            if (
                                container[AVALON_PROPERTY]["asset_name"]
                                == asset_name
                            ):
                                container_collection = container

        # Link the container collection to the scene collection
        # or if there is one collection in scene_collection choose
        # this collection
        if len(scene_collection.children) == 1:
            is_pyblish_container = plugin.is_pyblish_avalon_container(
                scene_collection.children[0]
            )
        if len(scene_collection.children) == 1 and not is_pyblish_container:
            # we don't want to add an asset in another publish container
            plugin.link_collection_to_collection(
                container_collection, scene_collection.children[0]
            )
        else:
            plugin.link_collection_to_collection(
                container_collection, scene_collection
            )

        # Get all the object of the container.
        # The farest parents in first for override them first
        objects = plugin.get_all_objects_in_collection(container_collection)
        collections = plugin.get_all_collections_in_collection(
            container_collection
        )

        objects.reverse()

        # Clean
        bpy.data.orphans_purge(do_local_ids=False)
        plugin.deselect_all()

        # Override the container and the objects
        container_overridden = container_collection.override_create(
            remap_local_usages=True
        )

        for collection in collections:
            collection.override_create(remap_local_usages=True)
        for object in objects:
            object.override_create(remap_local_usages=True)

        for collection in collections:
            plugin.prepare_data(collection, container_collection.name)

        return container_overridden

    def process_asset(
        self,
        context: dict,
        name: str,
        namespace: Optional[str] = None,
        options: Optional[Dict] = None,
    ) -> Optional[List]:
        """
        Arguments:
            name: Use pre-defined name
            namespace: Use pre-defined namespace
            context: Full parenthood of representation to load
            options: Additional settings dictionary
        """

        # Setup variable to construct names
        libpath = self.fname
        asset = context["asset"]["name"]
        subset = context["subset"]["name"]
        asset_name = plugin.asset_name(asset, subset)

        # Process the load of the container
        avalon_container = self._process(libpath, asset_name)

        has_namespace = api.Session["AVALON_TASK"] not in [
            "Rigging",
            "Modeling",
        ]
        plugin.set_original_name_for_objects_container(
            avalon_container, has_namespace
        )

        objects = avalon_container.objects
        self[:] = objects
        return objects

    def exec_update(self, container: Dict, representation: Dict):
        """Update the loaded asset.

        This will remove all objects of the current collection, load the new
        ones and add them to the collection.
        If the objects of the collection are used in another collection they
        will not be removed, only unlinked. Normally this should not be the
        case though.
        """

        # Setup variable to construct names
        object_name = container["objectName"]
        asset_name = container["asset_name"]
        # Get the avalon_container with the object name
        avalon_container = bpy.data.collections.get(object_name)
        # Find the library path
        libpath = Path(api.get_representation_path(representation))

        assert container, f"The asset is not loaded: {container['objectName']}"
        assert (
            libpath
        ), "No existing library file found for {container['objectName']}"
        assert libpath.is_file(), f"The file doesn't exist: {libpath}"

        # Get the metadata in the container
        metadata = avalon_container.get(AVALON_PROPERTY)
        # Get the library path store in the metadata
        container_libpath = metadata["libpath"]

        normalized_container_libpath = str(
            Path(bpy.path.abspath(container_libpath)).resolve()
        )
        normalized_libpath = str(
            Path(bpy.path.abspath(str(libpath))).resolve()
        )
        self.log.debug(
            f"normalized_group_libpath:\n  '{normalized_container_libpath}'"
            f"\nnormalized_libpath:\n  '{normalized_libpath}'"
        )
        # If library exits do nothing
        if normalized_container_libpath == normalized_libpath:
            self.log.info("Library already loaded, not updating...")
            return

        # Add temp namesapce to avoid rename object during the update
        plugin.set_temp_namespace_for_objects_container(avalon_container)

        # Get the parent collections of the container to relink after update
        parent_collections = plugin.get_parent_collections(avalon_container)

        # Get a dictionary of the modifier parameters to
        # reset them after the update
        modifiers_dict = self._get_modifier_parameters(avalon_container)

        # Get a list of the driver targets to reset them after the update
        empty = self._store_drivers_in_an_empty(avalon_container)

        # Remove the container
        self._remove(avalon_container)

        # Update of the container
        container_override = self._process(str(libpath), asset_name)

        plugin.set_temp_namespace_for_objects_container(container_override)

        # relink the updated container to his parent collection
        if parent_collections:
            if (
                container_override
                in bpy.context.scene.collection.children.values()
            ):
                bpy.context.scene.collection.children.unlink(
                    container_override
                )
                for parent_collection in parent_collections:
                    plugin.link_collection_to_collection(
                        container_override, parent_collection
                    )

        # Reset the modifier parameters and the driver targets
        self._set_modifiers(modifiers_dict)
        self._set_drivers_from_empty(empty)

        plugin.set_original_name_for_objects_container(container_override)

        bpy.context.view_layer.update()
        plugin.remove_orphan_datablocks()

    def exec_remove(self, container: Dict) -> bool:
        """Remove an existing container from a Blender scene.

        Arguments:
            container (openpype:container-1.0): Container to remove,
                from `host.ls()`.

        Returns:
            bool: Whether the container was deleted.
        """
        # Setup variable to construct names
        object_name = container["objectName"]
        # Get the avalon_container with the object name
        avalon_container = bpy.data.collections.get(object_name)

        # Remove the container
        self._remove(avalon_container)

        return True

    def update_avalon_property(self, representation: Dict):
        """Set the avalon property with the representation data"""
        # Set the avalon property with the representation data
        asset = str(representation["context"]["asset"])
        subset = str(representation["context"]["subset"])
        asset_name = plugin.asset_name(asset, subset)

        # Get the container in the scene
        container = bpy.data.collections.get(asset_name)

        container_collection = None
        if container.override_library is None and container.library is None:
            # Check if the container isn't publish
            if container["avalon"].get("id") == "pyblish.avalon.instance":
                container_collection = container

        if container_collection:
            container_collection[AVALON_PROPERTY] = {
                "schema": "openpype:container-2.0",
                "id": AVALON_CONTAINER_ID,
                "name": asset,
                "namespace": container_collection.name,
                "loader": str(self.__class__.__name__),
                "representation": str(representation["_id"]),
                "libpath": str(representation["data"]["path"]),
                "asset_name": asset_name,
                "parent": str(representation["parent"]),
                "family": str(representation["context"]["family"]),
                "objectName": container_collection.name,
            }
