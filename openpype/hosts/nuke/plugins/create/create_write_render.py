from pprint import pformat
import nuke

from openpype.lib import (
    BoolDef,
    NumberDef,
    UISeparatorDef,
    UILabelDef
)
from openpype.hosts.nuke.api import plugin
from openpype.hosts.nuke.api.lib import (
    create_write_node)


class CreateWriteRender(plugin.NukeWriteCreator):
    identifier = "create_write_render"
    label = "Create Write Render"
    family = "render"
    icon = "sign-out"

    def get_pre_create_attr_defs(self):
        attr_defs = [
            BoolDef("use_selection", label="Use selection"),
            self._get_render_target_enum()
        ]
        return attr_defs

    def get_instance_attr_defs(self):
        attr_defs = [
            self._get_render_target_enum(),
            self._get_reviewable_bool()
        ]
        if "farm_rendering" in self.instance_attributes:
            attr_defs.extend([
                UISeparatorDef(),
                UILabelDef("Farm rendering attributes"),
                BoolDef("suspended_publish", label="Suspended publishing"),
                NumberDef(
                    "farm_priority",
                    label="Priority",
                    minimum=1,
                    maximum=99,
                    default=50
                ),
                NumberDef(
                    "farm_chunk",
                    label="Chunk size",
                    minimum=1,
                    maximum=99,
                    default=10
                ),
                NumberDef(
                    "farm_concurency",
                    label="Concurent tasks",
                    minimum=1,
                    maximum=10,
                    default=1
                )
            ])
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

        return create_write_node(
            subset_name,
            write_data,
            input=self.selected_node,
            prenodes=self.prenodes,
            **{
                "width": width,
                "height": height
            }
        )
