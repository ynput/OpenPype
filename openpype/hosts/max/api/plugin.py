# -*- coding: utf-8 -*-
"""3dsmax specific Avalon/Pyblish plugin definitions."""
from abc import ABCMeta

import six
from pymxs import runtime as rt

from openpype.lib import BoolDef
from openpype.pipeline import CreatedInstance, Creator, CreatorError

from .lib import imprint, lsattr, read

MS_CUSTOM_ATTRIB = """attributes "openPypeData"
(
    parameters main rollout:OPparams
    (
        all_handles type:#maxObjectTab tabSize:0 tabSizeVariable:on
        sel_list type:#stringTab tabSize:0 tabSizeVariable:on
    )

    rollout OPparams "OP Parameters"
    (
        listbox list_node "Node References" items:#()
        button button_add "Add to Container"
        button button_del "Delete from Container"

        fn node_to_name the_node =
        (
            handle = the_node.handle
            obj_name = the_node.name
            handle_name = obj_name + "<" + handle as string + ">"
            return handle_name
        )
        fn nodes_to_add node =
        (
            sceneObjs = #()
            if classOf node == Container do return false
            n = node as string
            for obj in Objects do
            (
                tmp_obj = obj as string
                append sceneObjs tmp_obj
            )
            if sel_list != undefined do
            (
                for obj in sel_list do
                (
                    idx = findItem sceneObjs obj
                    if idx do
                    (
                        deleteItem sceneObjs idx
                    )
                )
            )
            idx = findItem sceneObjs n
            if idx then return true else false
        )

        fn nodes_to_rmv node =
        (
            n = node as string
            idx = findItem sel_list n
            if idx then return true else false
        )

        on button_add pressed do
        (
            current_sel = selectByName title:"Select Objects to add to
            the Container" buttontext:"Add" filter:nodes_to_add
            if current_sel == undefined then return False
            temp_arr = #()
            i_node_arr = #()
            for c in current_sel do
            (
                handle_name = node_to_name c
                node_ref = NodeTransformMonitor node:c
                idx = finditem list_node.items handle_name
                if idx do (
                    continue
                )
                name = c as string
                append temp_arr handle_name
                append i_node_arr node_ref
                append sel_list name
            )
            all_handles = join i_node_arr all_handles
            list_node.items = join temp_arr list_node.items
        )

        on button_del pressed do
        (
            current_sel = selectByName title:"Select Objects to remove
            from the Container" buttontext:"Remove" filter: nodes_to_rmv
            if current_sel == undefined or current_sel.count == 0 then
            (
                return False
            )
            temp_arr = #()
            i_node_arr = #()
            new_i_node_arr = #()
            new_temp_arr = #()

            for c in current_sel do
            (
                node_ref = NodeTransformMonitor node:c as string
                handle_name = node_to_name c
                n = c as string
                tmp_all_handles = #()
                for i in all_handles do
                (
                    tmp = i as string
                    append tmp_all_handles tmp
                )
                idx = finditem tmp_all_handles node_ref
                if idx do
                (
                    new_i_node_arr = DeleteItem all_handles idx

                )
                idx = finditem list_node.items handle_name
                if idx do
                (
                    new_temp_arr = DeleteItem list_node.items idx
                )
                idx = finditem sel_list n
                if idx do
                (
                    sel_list = DeleteItem sel_list idx
                )
            )
            all_handles = join i_node_arr new_i_node_arr
            list_node.items = join temp_arr new_temp_arr
        )

        on OPparams open do
        (
            if all_handles.count != 0 then
            (
                temp_arr = #()
                for x in all_handles do
                (
                    if x.node == undefined do continue
                    handle_name = node_to_name x.node
                    append temp_arr handle_name
                )
                list_node.items = temp_arr
            )
        )
    )
)"""


class OpenPypeCreatorError(CreatorError):
    pass


class MaxCreatorBase(object):

    @staticmethod
    def cache_subsets(shared_data):
        if shared_data.get("max_cached_subsets") is not None:
            return shared_data

        shared_data["max_cached_subsets"] = {}
        cached_instances = lsattr("id", "pyblish.avalon.instance")
        for i in cached_instances:
            creator_id = rt.GetUserProp(i, "creator_identifier")
            if creator_id not in shared_data["max_cached_subsets"]:
                shared_data["max_cached_subsets"][creator_id] = [i.name]
            else:
                shared_data[
                    "max_cached_subsets"][creator_id].append(i.name)
        return shared_data

    @staticmethod
    def create_instance_node(node):
        """Create instance node.

        If the supplied node is existing node, it will be used to hold the
        instance, otherwise new node of type Dummy will be created.

        Args:
            node (rt.MXSWrapperBase, str): Node or node name to use.

        Returns:
            instance
        """
        if isinstance(node, str):
            node = rt.Container(name=node)

        attrs = rt.Execute(MS_CUSTOM_ATTRIB)
        modifier = rt.EmptyModifier()
        rt.addModifier(node, modifier)
        node.modifiers[0].name = "OP Data"
        rt.custAttributes.add(node.modifiers[0], attrs)

        return node


@six.add_metaclass(ABCMeta)
class MaxCreator(Creator, MaxCreatorBase):
    selected_nodes = []

    def create(self, subset_name, instance_data, pre_create_data):
        if pre_create_data.get("use_selection"):
            self.selected_nodes = rt.GetCurrentSelection()
        if rt.getNodeByName(subset_name):
            raise CreatorError(f"'{subset_name}' is already created..")

        instance_node = self.create_instance_node(subset_name)
        instance_data["instance_node"] = instance_node.name
        instance = CreatedInstance(
            self.family,
            subset_name,
            instance_data,
            self
        )
        if pre_create_data.get("use_selection"):

            node_list = []
            sel_list = []
            for i in self.selected_nodes:
                node_ref = rt.NodeTransformMonitor(node=i)
                node_list.append(node_ref)
                sel_list.append(str(i))

            # Setting the property
            rt.setProperty(
                instance_node.modifiers[0].openPypeData,
                "all_handles", node_list)
            rt.setProperty(
                instance_node.modifiers[0].openPypeData,
                "sel_list", sel_list)

        self._add_instance_to_context(instance)
        imprint(instance_node.name, instance.data_to_store())

        return instance

    def collect_instances(self):
        self.cache_subsets(self.collection_shared_data)
        for instance in self.collection_shared_data["max_cached_subsets"].get(self.identifier, []):  # noqa
            created_instance = CreatedInstance.from_existing(
                read(rt.GetNodeByName(instance)), self
            )
            self._add_instance_to_context(created_instance)

    def update_instances(self, update_list):
        for created_inst, changes in update_list:
            instance_node = created_inst.get("instance_node")
            new_values = {
                key: changes[key].new_value
                for key in changes.changed_keys
            }
            subset = new_values.get("subset", "")
            if subset and instance_node != subset:
                node = rt.getNodeByName(instance_node)
                new_subset_name = new_values["subset"]
                if rt.getNodeByName(new_subset_name):
                    raise CreatorError(
                        "The subset '{}' already exists.".format(
                            new_subset_name))
                instance_node = new_subset_name
                created_inst["instance_node"] = instance_node
                node.name = instance_node

            imprint(
                instance_node,
                created_inst.data_to_store(),
            )

    def remove_instances(self, instances):
        """Remove specified instance from the scene.

        This is only removing `id` parameter so instance is no longer
        instance, because it might contain valuable data for artist.

        """
        for instance in instances:
            instance_node = rt.GetNodeByName(
                instance.data.get("instance_node"))
            if instance_node:
                count = rt.custAttributes.count(instance_node.modifiers[0])
                rt.custAttributes.delete(instance_node.modifiers[0], count)
                rt.Delete(instance_node)

            self._remove_instance_from_context(instance)

    def get_pre_create_attr_defs(self):
        return [
            BoolDef("use_selection", label="Use selection")
        ]
