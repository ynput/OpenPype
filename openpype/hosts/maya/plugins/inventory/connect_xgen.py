from maya import cmds
import xgenm

from openpype.pipeline import (
    InventoryAction, get_representation_context, get_representation_path
)


class ConnectXgen(InventoryAction):
    """Connect Xgen with an animation or pointcache.
    """

    label = "Connect Xgen"
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
        source_object = source_container["objectName"]

        # Validate source representation is an alembic.
        source_path = get_representation_path(
            get_representation_context(
                source_container["representation"]
            )["representation"]
        ).replace("\\", "/")
        message = "Animation container \"{}\" is not an alembic:\n{}".format(
            source_container["namespace"], source_path
        )
        if not source_path.endswith(".abc"):
            self.display_warning(message)
            return

        # Target containers.
        target_containers = []
        for family, containers in containers_by_family.items():
            if family in ["animation", "pointcache"]:
                continue

            target_containers.extend(containers)

        # Inform user of connections from source representation to target
        # descriptions.
        descriptions_data = []
        connections_msg = ""
        for target_container in target_containers:
            reference_node = cmds.sets(
                target_container["objectName"], query=True
            )[0]
            palettes = cmds.ls(
                cmds.referenceQuery(reference_node, nodes=True),
                type="xgmPalette"
            )
            for palette in palettes:
                for description in xgenm.descriptions(palette):
                    descriptions_data.append([palette, description])
                    connections_msg += "\n{}/{}".format(palette, description)

        message = "Connecting \"{}\" to:\n".format(
            source_container["namespace"]
        )
        message += connections_msg
        choice = self.display_warning(message, show_cancel=True)
        if choice is False:
            return

        # Recreate "xgenContainers" attribute to reset.
        compound_name = "xgenContainers"
        attr = "{}.{}".format(source_object, compound_name)
        if cmds.objExists(attr):
            cmds.deleteAttr(attr)

        cmds.addAttr(
            source_object,
            longName=compound_name,
            attributeType="compound",
            numberOfChildren=1,
            multi=True
        )

        # Connect target containers.
        for target_container in target_containers:
            cmds.addAttr(
                source_object,
                longName="container",
                attributeType="message",
                parent=compound_name
            )
            index = target_containers.index(target_container)
            cmds.connectAttr(
                target_container["objectName"] + ".message",
                source_object + ".{}[{}].container".format(
                    compound_name, index
                )
            )

        # Setup cache on Xgen
        object = "SplinePrimitive"
        for palette, description in descriptions_data:
            xgenm.setAttr("useCache", "true", palette, description, object)
            xgenm.setAttr("liveMode", "false", palette, description, object)
            xgenm.setAttr(
                "cacheFileName", source_path, palette, description, object
            )

        # Refresh UI and viewport.
        de = xgenm.xgGlobal.DescriptionEditor
        de.refresh("Full")

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
