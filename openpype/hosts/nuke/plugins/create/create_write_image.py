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
from openpype.hosts.nuke.api.plugin import exposed_write_knobs


class CreateWriteImage(napi.NukeWriteCreator):
    identifier = "create_write_image"
    label = "Image (write)"
    family = "image"
    icon = "sign-out"

    instance_attributes = [
        "use_range_limit"
    ]
    default_variants = [
        "StillFrame",
        "MPFrame",
        "LayoutFrame"
    ]
    temp_rendering_path_template = (
        "{work}/renders/nuke/{subset}/{subset}.{frame}.{ext}")

    def get_pre_create_attr_defs(self):
        attr_defs = [
            BoolDef(
                "use_selection",
                default=not self.create_context.headless,
                label="Use selection"
            ),
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
            linked_knobs=self.get_linked_knobs(),
            **{
                "frame": nuke.frame()
            }
        )

        self._add_frame_range_limit(created_node, instance_data)

        self.integrate_links(created_node, outputs=True)

        return created_node

    def create(self, subset_name, instance_data, pre_create_data):
        subset_name = subset_name.format(**pre_create_data)

        # pass values from precreate to instance
        self.pass_pre_attributes_to_instance(
            instance_data,
            pre_create_data,
            [
                "active_frame",
                "render_target"
            ]
        )

        # make sure selected nodes are added
        self.set_selected_nodes(pre_create_data)

        # make sure subset name is unique
        self.check_existing_subset(subset_name)

        instance_node = self.create_instance_node(
            subset_name,
            instance_data,
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

            exposed_write_knobs(
                self.project_settings, self.__class__.__name__, instance_node
            )

            return instance

        except Exception as er:
            six.reraise(
                napi.NukeCreatorError,
                napi.NukeCreatorError("Creator error: {}".format(er)),
                sys.exc_info()[2]
            )

    def _add_frame_range_limit(self, write_node, instance_data):
        if "use_range_limit" not in self.instance_attributes:
            return

        active_frame = (
            instance_data["creator_attributes"].get("active_frame"))

        write_node.begin()
        for n in nuke.allNodes():
            # get write node
            if n.Class() in "Write":
                w_node = n
        write_node.end()

        w_node["use_limit"].setValue(True)
        w_node["first"].setValue(active_frame or nuke.frame())
        w_node["last"].setExpression("first")

        return write_node
