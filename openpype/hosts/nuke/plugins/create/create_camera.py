import nuke
from openpype.hosts.nuke.api import (
    NukeCreator,
    NukeCreatorError,
    maintained_selection
)
from openpype.hosts.nuke.api.lib import (
    create_camera_node_by_version
)


class CreateCamera(NukeCreator):
    """Add Publishable Camera"""

    identifier = "create_camera"
    label = "Camera (3d)"
    family = "camera"
    icon = "camera"

    # plugin attributes
    node_color = "0xff9100ff"

    def create_instance_node(
        self,
        node_name,
        knobs=None,
        parent=None,
        node_type=None
    ):
        with maintained_selection():
            if self.selected_nodes:
                node = self.selected_nodes[0]
                if node.Class() != "Camera3":
                    raise NukeCreatorError(
                        "Creator error: Select only camera node type")
                created_node = self.selected_nodes[0]
            else:
                created_node = create_camera_node_by_version()

            created_node["tile_color"].setValue(
                int(self.node_color, 16))

            created_node["name"].setValue(node_name)

            return created_node

    def create(self, subset_name, instance_data, pre_create_data):
        # make sure subset name is unique
        self.check_existing_subset(subset_name)

        instance = super(CreateCamera, self).create(
            subset_name,
            instance_data,
            pre_create_data
        )

        return instance

    def set_selected_nodes(self, pre_create_data):
        if pre_create_data.get("use_selection"):
            self.selected_nodes = nuke.selectedNodes()
            if self.selected_nodes == []:
                raise NukeCreatorError(
                    "Creator error: No active selection")
            elif len(self.selected_nodes) > 1:
                raise NukeCreatorError(
                    "Creator error: Select only one camera node")
        else:
            self.selected_nodes = []
