# -*- coding: utf-8 -*-
import sys
import six
from abc import (
    ABC,
    ABCMeta,
)

import unreal

from .pipeline import (
    create_publish_instance,
    imprint,
    lsinst,
    UNREAL_VERSION
)
from openpype.lib import (
    BoolDef,
    UILabelDef
)
from openpype.pipeline import (
    Creator,
    LoaderPlugin,
    CreatorError,
    CreatedInstance
)


class OpenPypeCreatorError(CreatorError):
    pass


@six.add_metaclass(ABCMeta)
class UnrealBaseCreator(Creator):
    """Base class for Unreal creator plugins."""
    root = "/Game/OpenPype/PublishInstances"
    suffix = "_INS"

    @staticmethod
    def cache_subsets(shared_data):
        """Cache instances for Creators to shared data.

        Create `unreal_cached_subsets` key when needed in shared data and
        fill it with all collected instances from the scene under its
        respective creator identifiers.

        If legacy instances are detected in the scene, create
        `unreal_cached_legacy_subsets` there and fill it with
        all legacy subsets under family as a key.

        Args:
            Dict[str, Any]: Shared data.

        Return:
            Dict[str, Any]: Shared data dictionary.

        """
        if shared_data.get("unreal_cached_subsets") is None:
            shared_data["unreal_cached_subsets"] = {}
            if shared_data.get("unreal_cached_legacy_subsets") is None:
                shared_data["unreal_cached_legacy_subsets"] = {}
            cached_instances = lsinst()
            for i in cached_instances:
                if not i.get("creator_identifier"):
                    # we have legacy instance
                    family = i.get("family")
                    if (family not in
                            shared_data["unreal_cached_legacy_subsets"]):
                        shared_data[
                            "unreal_cached_legacy_subsets"][family] = [i]
                    else:
                        shared_data[
                            "unreal_cached_legacy_subsets"][family].append(i)
                    continue

                creator_id = i.get("creator_identifier")
                if creator_id not in shared_data["unreal_cached_subsets"]:
                    shared_data["unreal_cached_subsets"][creator_id] = [i]
                else:
                    shared_data["unreal_cached_subsets"][creator_id].append(i)
        return shared_data

    def create(self, subset_name, instance_data, pre_create_data):
        try:
            instance_name = f"{subset_name}{self.suffix}"
            pub_instance = create_publish_instance(instance_name, self.root)

            instance_data["subset"] = subset_name
            instance_data["instance_path"] = f"{self.root}/{instance_name}"

            instance = CreatedInstance(
                self.family,
                subset_name,
                instance_data,
                self)
            self._add_instance_to_context(instance)

            pub_instance.set_editor_property('add_external_assets', True)
            assets = pub_instance.get_editor_property('asset_data_external')

            ar = unreal.AssetRegistryHelpers.get_asset_registry()

            for member in pre_create_data.get("members", []):
                obj = ar.get_asset_by_object_path(member).get_asset()
                assets.add(obj)

            imprint(f"{self.root}/{instance_name}", instance_data)

        except Exception as er:
            six.reraise(
                OpenPypeCreatorError,
                OpenPypeCreatorError(f"Creator error: {er}"),
                sys.exc_info()[2])

    def collect_instances(self):
        # cache instances if missing
        self.cache_subsets(self.collection_shared_data)
        for instance in self.collection_shared_data[
                "unreal_cached_subsets"].get(self.identifier, []):
            created_instance = CreatedInstance.from_existing(instance, self)
            self._add_instance_to_context(created_instance)

    def update_instances(self, update_list):
        unreal.log_warning(f"Update instances: {update_list}")
        for created_inst, _changes in update_list:
            instance_node = created_inst.get("instance_path", "")

            if not instance_node:
                unreal.log_warning(
                    f"Instance node not found for {created_inst}")

            new_values = {
                key: new_value
                for key, (_old_value, new_value) in _changes.items()
            }
            imprint(
                instance_node,
                new_values
            )

    def remove_instances(self, instances):
        for instance in instances:
            instance_node = instance.data.get("instance_path", "")
            if instance_node:
                unreal.EditorAssetLibrary.delete_asset(instance_node)

            self._remove_instance_from_context(instance)


@six.add_metaclass(ABCMeta)
class UnrealAssetCreator(UnrealBaseCreator):
    """Base class for Unreal creator plugins based on assets."""

    def create(self, subset_name, instance_data, pre_create_data):
        """Create instance of the asset.

        Args:
            subset_name (str): Name of the subset.
            instance_data (dict): Data for the instance.
            pre_create_data (dict): Data for the instance.

        Returns:
            CreatedInstance: Created instance.
        """
        try:
            # Check if instance data has members, filled by the plugin.
            # If not, use selection.
            if not pre_create_data.get("members"):
                pre_create_data["members"] = []

                if pre_create_data.get("use_selection"):
                    utilib = unreal.EditorUtilityLibrary
                    sel_objects = utilib.get_selected_assets()
                    pre_create_data["members"] = [
                        a.get_path_name() for a in sel_objects]

            super(UnrealAssetCreator, self).create(
                subset_name,
                instance_data,
                pre_create_data)

        except Exception as er:
            six.reraise(
                OpenPypeCreatorError,
                OpenPypeCreatorError(f"Creator error: {er}"),
                sys.exc_info()[2])

    def get_pre_create_attr_defs(self):
        return [
            BoolDef("use_selection", label="Use selection", default=True)
        ]


@six.add_metaclass(ABCMeta)
class UnrealActorCreator(UnrealBaseCreator):
    """Base class for Unreal creator plugins based on actors."""

    def create(self, subset_name, instance_data, pre_create_data):
        """Create instance of the asset.

        Args:
            subset_name (str): Name of the subset.
            instance_data (dict): Data for the instance.
            pre_create_data (dict): Data for the instance.

        Returns:
            CreatedInstance: Created instance.
        """
        try:
            if UNREAL_VERSION.major == 5:
                world = unreal.UnrealEditorSubsystem().get_editor_world()
            else:
                world = unreal.EditorLevelLibrary.get_editor_world()

            # Check if the level is saved
            if world.get_path_name().startswith("/Temp/"):
                raise OpenPypeCreatorError(
                    "Level must be saved before creating instances.")

            # Check if instance data has members, filled by the plugin.
            # If not, use selection.
            if not instance_data.get("members"):
                selection = []

                if pre_create_data.get("use_selection"):
                    utility_lib = unreal.EditorUtilityLibrary
                    sel_objects = utility_lib.get_selected_assets()
                    selection = [a.get_path_name() for a in sel_objects]

                instance_data["members"] = selection

            instance_data["level"] = world.get_path_name()

            super(UnrealActorCreator, self).create(
                subset_name,
                instance_data,
                pre_create_data)

        except Exception as er:
            six.reraise(
                OpenPypeCreatorError,
                OpenPypeCreatorError(f"Creator error: {er}"),
                sys.exc_info()[2])

    def get_pre_create_attr_defs(self):
        return [
            UILabelDef("Select actors to create instance from them.")
        ]


class Loader(LoaderPlugin, ABC):
    """This serves as skeleton for future OpenPype specific functionality"""
    pass
