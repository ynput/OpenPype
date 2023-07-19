# -*- coding: utf-8 -*-
import ast
import collections
import sys
import six
from abc import ABCMeta

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
from openpype.hosts.unreal.api.pipeline import (
    send_request,
    unreal_log,
    ls_inst,
    imprint,
    containerise,
    instantiate
)


@six.add_metaclass(ABCMeta)
class UnrealBaseCreator(Creator):
    """Base class for Unreal creator plugins."""
    root = "/Game/Ayon/AyonPublishInstances"
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
            unreal_cached_subsets = collections.defaultdict(list)
            unreal_cached_legacy_subsets = collections.defaultdict(list)
            for instance in ls_inst():
                if creator_id := instance.get("creator_identifier"):
                    unreal_cached_subsets[creator_id].append(instance)
                else:
                    family = instance.get("family")
                    unreal_cached_legacy_subsets[family].append(instance)

            shared_data["unreal_cached_subsets"] = unreal_cached_subsets
            shared_data["unreal_cached_legacy_subsets"] = (
                unreal_cached_legacy_subsets
            )
        return shared_data

    def create(self, subset_name, instance_data, pre_create_data):
        try:
            instance_name = f"{subset_name}{self.suffix}"

            instance_data["subset"] = subset_name
            instance_data["instance_path"] = f"{self.root}/{instance_name}"

            instance = CreatedInstance(
                self.family,
                subset_name,
                instance_data,
                self)
            self._add_instance_to_context(instance)

            instantiate(
                self.root,
                instance_name,
                instance.data_to_store(),
                pre_create_data.get("members", []))

            return instance

        except Exception as er:
            six.reraise(
                CreatorError,
                CreatorError(f"Creator error: {er}"),
                sys.exc_info()[2])

    def collect_instances(self):
        # cache instances if missing
        self.cache_subsets(self.collection_shared_data)
        for instance in self.collection_shared_data[
                "unreal_cached_subsets"].get(self.identifier, []):
            # Unreal saves metadata as string, so we need to convert it back
            instance['creator_attributes'] = ast.literal_eval(
                instance.get('creator_attributes', '{}'))
            instance['publish_attributes'] = ast.literal_eval(
                instance.get('publish_attributes', '{}'))
            created_instance = CreatedInstance.from_existing(instance, self)
            self._add_instance_to_context(created_instance)

    def update_instances(self, update_list):
        for created_inst, changes in update_list:
            instance_node = created_inst.get("instance_path", "")

            if not instance_node:
                message = f"Instance node not found for {created_inst}"
                unreal_log(message, "warning")
                continue

            new_values = {
                key: changes[key].new_value
                for key in changes.changed_keys
            }
            imprint(instance_node, new_values)

    def remove_instances(self, instances):
        for instance in instances:
            if instance_node := instance.data.get("instance_path", ""):
                send_request(
                    "delete_asset", params={"asset_path": instance_node})

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
                    pre_create_data["members"] = send_request(
                        "get_selected_assets")

            super(UnrealAssetCreator, self).create(
                subset_name,
                instance_data,
                pre_create_data)

        except Exception as er:
            six.reraise(
                CreatorError,
                CreatorError(f"Creator error: {er}"),
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
            world = send_request("get_editor_world")

            # Check if the level is saved
            if world.startswith("/Temp/"):
                raise CreatorError(
                    "Level must be saved before creating instances.")

            # Check if instance data has members, filled by the plugin.
            # If not, use selection.
            if not instance_data.get("members"):
                instance_data["members"] = send_request(
                    "get_selected_actors")

            instance_data["level"] = world

            super(UnrealActorCreator, self).create(
                subset_name,
                instance_data,
                pre_create_data)

        except Exception as er:
            six.reraise(
                CreatorError,
                CreatorError(f"Creator error: {er}"),
                sys.exc_info()[2])

    def get_pre_create_attr_defs(self):
        return [
            UILabelDef("Select actors to create instance from them.")
        ]


@six.add_metaclass(ABCMeta)
class UnrealBaseLoader(LoaderPlugin):
    """Base class for Unreal loader plugins."""
    root = "/Game/Ayon"
    suffix = "_CON"

    def update(self, container, representation):
        asset_dir = container["namespace"]
        container_name = container['objectName']

        data = {
            "representation": str(representation["_id"]),
            "parent": str(representation["parent"])
        }

        imprint(f"{asset_dir}/{container_name}", data)

    def remove(self, container):
        path = container["namespace"]

        send_request("remove_asset", params={"path": path})
