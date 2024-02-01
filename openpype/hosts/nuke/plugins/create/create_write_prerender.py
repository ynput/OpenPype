import nuke
import sys
import six

from openpype.pipeline import (
    CreatedInstance
)
from openpype.lib import (
    BoolDef
)
from openpype.hosts.nuke import api as napi
from openpype.hosts.nuke.api.plugin import exposed_write_knobs


class CreateWritePrerender(napi.NukeWriteCreator):
    identifier = "create_write_prerender"
    label = "Prerender (write)"
    family = "prerender"
    icon = "sign-out"

    instance_attributes = [
        "use_range_limit"
    ]
    default_variants = [
        "Key01",
        "Bg01",
        "Fg01",
        "Branch01",
        "Part01"
    ]
    temp_rendering_path_template = (
        "{work}/renders/nuke/{subset}/{subset}.{frame}.{ext}")

    # Before write node render.
    order = 90

    def get_pre_create_attr_defs(self):
        attr_defs = [
            BoolDef(
                "use_selection",
                default=not self.create_context.headless,
                label="Use selection"
            ),
            self._get_render_target_enum()
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

        # get width and height
        if self.selected_node:
            width, height = (
                self.selected_node.width(), self.selected_node.height())
        else:
            actual_format = nuke.root().knob('format').value()
            width, height = (actual_format.width(), actual_format.height())

        created_node = napi.create_write_node(
            subset_name,
            write_data,
            input=self.selected_node,
            prenodes=self.prenodes,
            linked_knobs=self.get_linked_knobs(),
            **{
                "width": width,
                "height": height
            }
        )

        self._add_frame_range_limit(created_node)

        self.integrate_links(created_node, outputs=True)

        return created_node

    def create(self, subset_name, instance_data, pre_create_data):
        # pass values from precreate to instance
        self.pass_pre_attributes_to_instance(
            instance_data,
            pre_create_data,
            [
                "render_target"
            ]
        )

        # make sure selected nodes are added
        self.set_selected_nodes(pre_create_data)

        # make sure subset name is unique
        self.check_existing_subset(subset_name)

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

    def _add_frame_range_limit(self, write_node):
        if "use_range_limit" not in self.instance_attributes:
            return

        write_node.begin()
        for n in nuke.allNodes():
            # get write node
            if n.Class() in "Write":
                w_node = n
        write_node.end()

        w_node["use_limit"].setValue(True)
        w_node["first"].setValue(nuke.root()["first_frame"].value())
        w_node["last"].setValue(nuke.root()["last_frame"].value())

        return write_node
