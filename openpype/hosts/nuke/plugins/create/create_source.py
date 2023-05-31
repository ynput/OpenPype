import nuke
import six
import sys
from openpype.hosts.nuke.api import (
    INSTANCE_DATA_KNOB,
    NukeCreator,
    NukeCreatorError,
    set_node_data
)
from openpype.pipeline import (
    CreatedInstance
)


class CreateSource(NukeCreator):
    """Add Publishable Read with source"""

    identifier = "create_source"
    label = "Source (read)"
    family = "source"
    icon = "film"
    default_variants = ["Effect", "Backplate", "Fire", "Smoke"]

    # plugin attributes
    node_color = "0xff9100ff"

    def create_instance_node(
        self,
        node_name,
        read_node
    ):
        read_node["tile_color"].setValue(
            int(self.node_color, 16))
        read_node["name"].setValue(node_name)

        return read_node

    def create(self, subset_name, instance_data, pre_create_data):

        # make sure selected nodes are added
        self.set_selected_nodes(pre_create_data)

        try:
            for read_node in self.selected_nodes:
                if read_node.Class() != 'Read':
                    continue

                node_name = read_node.name()
                _subset_name = subset_name + node_name

                # make sure subset name is unique
                self.check_existing_subset(_subset_name)

                instance_node = self.create_instance_node(
                    _subset_name,
                    read_node
                )
                instance = CreatedInstance(
                    self.family,
                    _subset_name,
                    instance_data,
                    self
                )

                instance.transient_data["node"] = instance_node

                self._add_instance_to_context(instance)

                set_node_data(
                    instance_node,
                    INSTANCE_DATA_KNOB,
                    instance.data_to_store()
                )

        except Exception as er:
            six.reraise(
                NukeCreatorError,
                NukeCreatorError("Creator error: {}".format(er)),
                sys.exc_info()[2])

    def set_selected_nodes(self, pre_create_data):
        if pre_create_data.get("use_selection"):
            self.selected_nodes = nuke.selectedNodes()
            if self.selected_nodes == []:
                raise NukeCreatorError("Creator error: No active selection")
        else:
            NukeCreatorError(
                "Creator error: only supported with active selection")
