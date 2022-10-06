import nuke
import sys
import six

from openpype.pipeline import (
    CreatedInstance
)
from openpype.lib import (
    BoolDef,
    NumberDef,
    UISeparatorDef,
    EnumDef
)
from openpype.hosts.nuke import api as napi


class CreateWriteStill(napi.NukeWriteCreator):
    identifier = "create_write_still"
    label = "Create Write Still Frame"
    family = "still"
    icon = "sign-out"

    def get_pre_create_attr_defs(self):
        attr_defs = [
            BoolDef("use_selection", label="Use selection"),
            self._get_render_target_enum(),
            UISeparatorDef(),
            self._get_frame_source_number()
        ]
        return attr_defs

    def _get_render_target_enum(self):
        rendering_targets = {
            "local": "Local machine rendering",
            "frames": "Use existing frames"
        }

        return EnumDef(
            "render_target",
            items=rendering_targets,
            label="Render target"
        )

    def _get_frame_source_number(self):
        return NumberDef(
            "active_frame",
            label="Active frame",
            default=nuke.frame()
        )

    def get_instance_attr_defs(self):
        attr_defs = [
            self._get_render_target_enum(),
            self._get_reviewable_bool()
        ]
        return attr_defs

    def create_instance_node(self, subset_name, instance_data):
        # add fpath_template
        write_data = {
            "creator": self.__class__.__name__,
            "subset": subset_name,
            "fpath_template": self.temp_rendering_path_template
        }

        write_data.update(instance_data)

        created_node = napi.create_write_node(
            subset_name,
            write_data,
            input=self.selected_node,
            prenodes=self.prenodes,
            linked_knobs=["channels", "___", "first", "last", "use_limit"],
            **{
                "frame": nuke.frame()
            }
        )
        self.add_info_knob(created_node)

        self._add_frame_range_limit(created_node)

        self.integrate_links(created_node, outputs=False)

        return created_node

    def create(self, subset_name, instance_data, pre_create_data):
        subset_name = subset_name.format(**pre_create_data)

        # make sure selected nodes are added
        self.set_selected_nodes(pre_create_data)

        # make sure subset name is unique
        if self.check_existing_subset(subset_name, instance_data):
            raise napi.NukeCreatorError(
                ("subset {} is already published"
                 "definition.").format(subset_name))

        instance_node = self.create_instance_node(
            subset_name,
            instance_data
        )

        try:
            instance = CreatedInstance(
                self.family,
                subset_name,
                instance_data,
                self
            )

            instance.transient_data["node"] = instance_node

            self._add_instance_to_context(instance)

            napi.set_node_data(
                instance_node,
                napi.INSTANCE_DATA_KNOB,
                instance.data_to_store()
            )

            return instance

        except Exception as er:
            six.reraise(
                napi.NukeCreatorError,
                napi.NukeCreatorError("Creator error: {}".format(er)),
                sys.exc_info()[2]
            )

    def _add_frame_range_limit(self, write_node):
        write_node.begin()
        for n in nuke.allNodes():
            # get write node
            if n.Class() in "Write":
                w_node = n
        write_node.end()

        w_node["use_limit"].setValue(True)
        w_node["first"].setValue(nuke.frame())
        w_node["last"].setValue(nuke.frame())

        return write_node
