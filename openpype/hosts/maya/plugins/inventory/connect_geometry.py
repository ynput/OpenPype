from maya import cmds

from openpype.pipeline import InventoryAction, get_representation_context
from openpype.hosts.maya.api.lib import get_id


class ConnectGeometry(InventoryAction):
    """Connect geometries within containers.

    Source container will connect to the target containers, by searching for
    matching geometry IDs (cbid).
    Source containers are of family; "animation" and "pointcache".
    The connection with be done with a live world space blendshape.
    """

    label = "Connect Geometry"
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

        source_object = source_containers[0]["objectName"]

        # Collect matching geometry transforms based cbId attribute.
        target_containers = []
        for family, containers in containers_by_family.items():
            if family in ["animation", "pointcache"]:
                continue

            target_containers.extend(containers)

        source_data = self.get_container_data(source_object)
        matches = []
        node_types = set()
        for target_container in target_containers:
            target_data = self.get_container_data(
                target_container["objectName"]
            )
            node_types.update(target_data["node_types"])
            for id, transform in target_data["ids"].items():
                source_match = source_data["ids"].get(id)
                if source_match:
                    matches.append([source_match, transform])

        # Message user about what is about to happen.
        if not matches:
            self.display_warning("No matching geometries found.")
            return

        message = "Connecting geometries:\n\n"
        for match in matches:
            message += "{} > {}\n".format(match[0], match[1])

        choice = self.display_warning(message, show_cancel=True)
        if choice is False:
            return

        # Setup live worldspace blendshape connection.
        for source, target in matches:
            blendshape = cmds.blendShape(source, target)[0]
            cmds.setAttr(blendshape + ".origin", 0)
            cmds.setAttr(blendshape + "." + target.split(":")[-1], 1)

        # Update Xgen if in any of the containers.
        if "xgmPalette" in node_types:
            cmds.xgmPreview()

    def get_container_data(self, container):
        """Collects data about the container nodes.

        Args:
            container (dict): Container instance.

        Returns:
            data (dict):
                "node_types": All node types in container nodes.
                "ids": If the node is a mesh, we collect its parent transform
                    id.
        """
        data = {"node_types": set(), "ids": {}}
        ref_node = cmds.sets(container, query=True, nodesOnly=True)[0]
        for node in cmds.referenceQuery(ref_node, nodes=True):
            node_type = cmds.nodeType(node)
            data["node_types"].add(node_type)

            # Only interested in mesh transforms for connecting geometry with
            # blendshape.
            if node_type != "mesh":
                continue

            transform = cmds.listRelatives(node, parent=True)[0]
            data["ids"][get_id(transform)] = transform

        return data

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
