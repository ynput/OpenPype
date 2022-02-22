# -*- coding: utf-8 -*-
"""Look loader."""
import json
from collections import defaultdict

from Qt import QtWidgets

from avalon import api, io
import openpype.hosts.maya.api.plugin
from openpype.hosts.maya.api import lib
from openpype.widgets.message_window import ScrollMessageBox

from openpype.hosts.maya.api.plugin import get_reference_node


class LookLoader(openpype.hosts.maya.api.plugin.ReferenceLoader):
    """Specific loader for lookdev"""

    families = ["look"]
    representations = ["ma"]

    label = "Reference look"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, options):
        import maya.cmds as cmds

        with lib.maintained_selection():
            nodes = cmds.file(self.fname,
                              namespace=namespace,
                              reference=True,
                              returnNewNodes=True)

        self[:] = nodes

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):
        """
            Called by Scene Inventory when look should be updated to current
            version.
            If any reference edits cannot be applied, eg. shader renamed and
            material not present, reference is unloaded and cleaned.
            All failed edits are highlighted to the user via message box.

        Args:
            container: object that has look to be updated
            representation: (dict): relationship data to get proper
                                       representation from DB and persisted
                                       data in .json
        Returns:
            None
        """
        from maya import cmds

        # Get reference node from container members
        members = lib.get_container_members(container)
        reference_node = get_reference_node(members, log=self.log)

        shader_nodes = cmds.ls(members, type='shadingEngine')
        orig_nodes = set(self._get_nodes_with_shader(shader_nodes))

        # Trigger the regular reference update on the ReferenceLoader
        super(LookLoader, self).update(container, representation)

        # get new applied shaders and nodes from new version
        shader_nodes = cmds.ls(members, type='shadingEngine')
        nodes = set(self._get_nodes_with_shader(shader_nodes))

        json_representation = io.find_one({
            "type": "representation",
            "parent": representation['parent'],
            "name": "json"
        })

        # Load relationships
        shader_relation = api.get_representation_path(json_representation)
        with open(shader_relation, "r") as f:
            json_data = json.load(f)

        # update of reference could result in failed edits - material is not
        # present because of renaming etc. If so highlight failed edits to user
        failed_edits = cmds.referenceQuery(reference_node,
                                           editStrings=True,
                                           failedEdits=True,
                                           successfulEdits=False)
        if failed_edits:
            # clean references - removes failed reference edits
            cmds.file(cr=reference_node)  # cleanReference

            # reapply shading groups from json representation on orig nodes
            lib.apply_shaders(json_data, shader_nodes, orig_nodes)

            msg = ["During reference update some edits failed.",
                   "All successful edits were kept intact.\n",
                   "Failed and removed edits:"]
            msg.extend(failed_edits)

            msg = ScrollMessageBox(QtWidgets.QMessageBox.Warning,
                                   "Some reference edit failed",
                                   msg)
            msg.exec_()

        attributes = json_data.get("attributes", [])

        # region compute lookup
        nodes_by_id = defaultdict(list)
        for n in nodes:
            nodes_by_id[lib.get_id(n)].append(n)
        lib.apply_attributes(attributes, nodes_by_id)

    def _get_nodes_with_shader(self, shader_nodes):
        """
            Returns list of nodes belonging to specific shaders
        Args:
            shader_nodes: <list> of Shader groups
        Returns
            <list> node names
        """
        import maya.cmds as cmds

        nodes_list = []
        for shader in shader_nodes:
            connections = cmds.listConnections(cmds.listHistory(shader, f=1),
                                               type='mesh')
            if connections:
                for connection in connections:
                    nodes_list.extend(cmds.listRelatives(connection,
                                                         shapes=True))
        return nodes_list
