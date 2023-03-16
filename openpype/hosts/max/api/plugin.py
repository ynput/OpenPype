# -*- coding: utf-8 -*-
"""3dsmax specific Avalon/Pyblish plugin definitions."""
from pymxs import runtime as rt
import six
from abc import ABCMeta
from openpype.pipeline import (
    CreatorError,
    Creator,
    CreatedInstance
)
from openpype.lib import BoolDef
from .lib import imprint, read, lsattr


class OpenPypeCreatorError(CreatorError):
    pass


class MaxCreatorBase(object):

    @staticmethod
    def cache_subsets(shared_data):
        if shared_data.get("max_cached_subsets") is None:
            shared_data["max_cached_subsets"] = {}
            cached_instances = lsattr("id", "pyblish.avalon.instance")
            for i in cached_instances:
                creator_id = rt.getUserProp(i, "creator_identifier")
                if creator_id not in shared_data["max_cached_subsets"]:
                    shared_data["max_cached_subsets"][creator_id] = [i.name]
                else:
                    shared_data[
                        "max_cached_subsets"][creator_id].append(i.name)  # noqa
        return shared_data

    @staticmethod
    def create_instance_node(node_name: str, parent: str = ""):
        parent_node = rt.getNodeByName(parent) if parent else rt.rootScene
        if not parent_node:
            raise OpenPypeCreatorError(f"Specified parent {parent} not found")

        container = rt.container(name=node_name)
        container.Parent = parent_node

        return container


@six.add_metaclass(ABCMeta)
class MaxCreator(Creator, MaxCreatorBase):
    selected_nodes = []

    def create(self, subset_name, instance_data, pre_create_data):
        if pre_create_data.get("use_selection"):
            self.selected_nodes = rt.getCurrentSelection()

        instance_node = self.create_instance_node(subset_name)
        instance_data["instance_node"] = instance_node.name
        instance = CreatedInstance(
            self.family,
            subset_name,
            instance_data,
            self
        )
        for node in self.selected_nodes:
            node.Parent = instance_node

        self._add_instance_to_context(instance)
        imprint(instance_node.name, instance.data_to_store())

        return instance

    def collect_instances(self):
        self.cache_subsets(self.collection_shared_data)
        for instance in self.collection_shared_data[
                "max_cached_subsets"].get(self.identifier, []):
            created_instance = CreatedInstance.from_existing(
                read(rt.getNodeByName(instance)), self
            )
            self._add_instance_to_context(created_instance)

    def update_instances(self, update_list):
        for created_inst, changes in update_list:
            instance_node = created_inst.get("instance_node")

            new_values = {
                key: changes[key].new_value
                for key in changes.changed_keys
            }
            imprint(
                instance_node,
                new_values,
            )

    def remove_instances(self, instances):
        """Remove specified instance from the scene.

        This is only removing `id` parameter so instance is no longer
        instance, because it might contain valuable data for artist.

        """
        for instance in instances:
            instance_node = rt.getNodeByName(
                instance.data.get("instance_node"))
            if instance_node:
                rt.select(instance_node)
                rt.execute(f'for o in selection do for c in o.children do c.parent = undefined')    # noqa
                rt.delete(instance_node)

            self._remove_instance_from_context(instance)

    def get_pre_create_attr_defs(self):
        return [
            BoolDef("use_selection", label="Use selection")
        ]
