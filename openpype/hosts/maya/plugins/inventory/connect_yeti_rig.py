import os
import json

from maya import cmds

from openpype.pipeline import (
    InventoryAction, get_representation_context, get_representation_path
)


class ConnectYetiRig(InventoryAction):
    """Connect Yeti Rig with an animation or pointcache."""

    label = "Connect Yeti Rig"
    icon = "link"
    color = "white"

    def process(self, containers):
        # Validate selection is more than 1.
        message = (
            "Only 1 container selected. 2+ containers needed for this action."
        )
        if len(containers) == 1:
            self.display_warning(message)
            return

        # Categorize containers by family.
        containers_by_family = {}
        for container in containers:
            family = get_representation_context(
                container["representation"]
            )["subset"]["data"]["family"]
            try:
                containers_by_family[family].append(container)
            except KeyError:
                containers_by_family[family] = [container]

        # Validate to only 1 source container.
        source_containers = containers_by_family.get("animation", [])
        source_containers += containers_by_family.get("pointcache", [])
        source_container_namespaces = [
            x["namespace"] for x in source_containers
        ]
        message = (
            "{} animation containers selected:\n\n{}\n\nOnly select 1 of type "
            "\"animation\" or \"pointcache\".".format(
                len(source_containers), source_container_namespaces
            )
        )
        if len(source_containers) != 1:
            self.display_warning(message)
            return

        source_container = source_containers[0]
        source_ids = self.index_by_id(source_container)

        # Target containers.
        target_ids = {}
        inputs = []
        for family, containers in containers_by_family.items():
            if family != "yetiRig":
                continue

            for container in containers:
                target_ids.update(self.index_by_id(container))

                maya_file = get_representation_path(
                    get_representation_context(
                        container["representation"]
                    )["representation"]
                )
                _, ext = os.path.splitext(maya_file)
                settings_file = maya_file.replace(ext, ".rigsettings")
                if not os.path.exists(settings_file):
                    continue

                with open(settings_file) as f:
                    inputs.extend(json.load(f)["inputs"])

        # Compare loaded connections to scene.
        for input in inputs:
            source_node = source_ids.get(input["sourceID"])
            target_node = target_ids.get(input["destinationID"])

            if not source_node or not target_node:
                self.log.debug(
                    "Could not find nodes for input:\n" +
                    json.dumps(input, indent=4, sort_keys=True)
                )
                continue
            source_attr, target_attr = input["connections"]
            
            if not cmds.attributeQuery(source_attr, node=source_node, exists=True):
                self.log.debug(
                    "Could not find attribute {} on node {} for input:\n{}".format(
                    source_attr, source_node, json.dumps(input, indent=4, sort_keys=True)
                )
                continue
            
            if not cmds.attributeQuery(target_node, node=target_attr, exists=True):
                self.log.debug(
                    "Could not find attribute {} on node {} for input:\n{}".format(
                    target_attr, target_node, json.dumps(input, indent=4, sort_keys=True)
                )
                continue
            
            cmds.connectAttr(
                "{}.{}".format(source_node, source_attr),
                "{}.{}".format(target_node, target_attr)
            )

    def index_by_id(self, container):
        reference_node = cmds.sets(container["objectName"], query=True)
        members = cmds.referenceQuery(reference_node, nodes=True, dagPath=True)

        ids = {}
        for member in members:
            if not cmds.objExists(member + ".cbId"):
                continue
            ids[cmds.getAttr(member + ".cbId")] = member

        return ids

    def display_warning(self, message, show_cancel=False):
        """Show feedback to user.

        Returns:
            bool
        """

        from qtpy import QtWidgets

        accept = QtWidgets.QMessageBox.Ok
        if show_cancel:
            buttons = accept | QtWidgets.QMessageBox.Cancel
        else:
            buttons = accept

        state = QtWidgets.QMessageBox.warning(
            None,
            "",
            message,
            buttons=buttons,
            defaultButton=accept
        )

        return state == accept
