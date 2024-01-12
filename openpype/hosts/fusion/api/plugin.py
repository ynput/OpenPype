from copy import deepcopy
import os

from openpype.hosts.fusion.api import (
    get_current_comp,
    comp_lock_and_undo_chunk,
)

from openpype.lib import (
    BoolDef,
    EnumDef,
)
from openpype.pipeline import (
    legacy_io,
    Creator,
    CreatedInstance
)


class GenericCreateSaver(Creator):
    default_variants = ["Main", "Mask"]
    description = "Fusion Saver to generate image sequence"
    icon = "fa5.eye"

    instance_attributes = [
        "reviewable"
    ]

    settings_category = "fusion"

    image_format = "exr"

    # TODO: This should be renamed together with Nuke so it is aligned
    temp_rendering_path_template = (
        "{workdir}/renders/fusion/{subset}/{subset}.{frame}.{ext}")

    def create(self, subset_name, instance_data, pre_create_data):
        self.pass_pre_attributes_to_instance(instance_data, pre_create_data)

        instance = CreatedInstance(
            family=self.family,
            subset_name=subset_name,
            data=instance_data,
            creator=self,
        )
        data = instance.data_to_store()
        comp = get_current_comp()
        with comp_lock_and_undo_chunk(comp):
            args = (-32768, -32768)  # Magical position numbers
            saver = comp.AddTool("Saver", *args)

            self._update_tool_with_data(saver, data=data)

        # Register the CreatedInstance
        self._imprint(saver, data)

        # Insert the transient data
        instance.transient_data["tool"] = saver

        self._add_instance_to_context(instance)

        return instance

    def collect_instances(self):
        comp = get_current_comp()
        tools = comp.GetToolList(False, "Saver").values()
        for tool in tools:
            data = self.get_managed_tool_data(tool)
            if not data:
                continue

            # Add instance
            created_instance = CreatedInstance.from_existing(data, self)

            # Collect transient data
            created_instance.transient_data["tool"] = tool

            self._add_instance_to_context(created_instance)

    def update_instances(self, update_list):
        for created_inst, _changes in update_list:
            new_data = created_inst.data_to_store()
            tool = created_inst.transient_data["tool"]
            self._update_tool_with_data(tool, new_data)
            self._imprint(tool, new_data)

    def remove_instances(self, instances):
        for instance in instances:
            # Remove the tool from the scene

            tool = instance.transient_data["tool"]
            if tool:
                tool.Delete()

            # Remove the collected CreatedInstance to remove from UI directly
            self._remove_instance_from_context(instance)

    def _imprint(self, tool, data):
        # Save all data in a "openpype.{key}" = value data

        # Instance id is the tool's name so we don't need to imprint as data
        data.pop("instance_id", None)

        active = data.pop("active", None)
        if active is not None:
            # Use active value to set the passthrough state
            tool.SetAttrs({"TOOLB_PassThrough": not active})

        for key, value in data.items():
            tool.SetData(f"openpype.{key}", value)

    def _update_tool_with_data(self, tool, data):
        """Update tool node name and output path based on subset data"""
        if "subset" not in data:
            return

        original_subset = tool.GetData("openpype.subset")
        original_format = tool.GetData(
            "openpype.creator_attributes.image_format"
        )

        subset = data["subset"]
        if (
            original_subset != subset
            or original_format != data["creator_attributes"]["image_format"]
        ):
            self._configure_saver_tool(data, tool, subset)

    def _configure_saver_tool(self, data, tool, subset):
        formatting_data = deepcopy(data)

        # get frame padding from anatomy templates
        frame_padding = self.project_anatomy.templates["frame_padding"]

        # get output format
        ext = data["creator_attributes"]["image_format"]

        # Subset change detected
        workdir = os.path.normpath(legacy_io.Session["AVALON_WORKDIR"])
        formatting_data.update({
            "workdir": workdir,
            "frame": "0" * frame_padding,
            "ext": ext,
            "product": {
                "name": formatting_data["subset"],
                "type": formatting_data["family"],
            },
        })

        # build file path to render
        filepath = self.temp_rendering_path_template.format(**formatting_data)

        comp = get_current_comp()
        tool["Clip"] = comp.ReverseMapPath(os.path.normpath(filepath))

        # Rename tool
        if tool.Name != subset:
            print(f"Renaming {tool.Name} -> {subset}")
            tool.SetAttrs({"TOOLS_Name": subset})

    def get_managed_tool_data(self, tool):
        """Return data of the tool if it matches creator identifier"""
        data = tool.GetData("openpype")
        if not isinstance(data, dict):
            return

        required = {
            "id": "pyblish.avalon.instance",
            "creator_identifier": self.identifier,
        }
        for key, value in required.items():
            if key not in data or data[key] != value:
                return

        # Get active state from the actual tool state
        attrs = tool.GetAttrs()
        passthrough = attrs["TOOLB_PassThrough"]
        data["active"] = not passthrough

        # Override publisher's UUID generation because tool names are
        # already unique in Fusion in a comp
        data["instance_id"] = tool.Name

        return data

    def get_instance_attr_defs(self):
        """Settings for publish page"""
        return self.get_pre_create_attr_defs()

    def pass_pre_attributes_to_instance(self, instance_data, pre_create_data):
        creator_attrs = instance_data["creator_attributes"] = {}
        for pass_key in pre_create_data.keys():
            creator_attrs[pass_key] = pre_create_data[pass_key]

    def _get_render_target_enum(self):
        rendering_targets = {
            "local": "Local machine rendering",
            "frames": "Use existing frames",
        }
        if "farm_rendering" in self.instance_attributes:
            rendering_targets["farm"] = "Farm rendering"

        return EnumDef(
            "render_target", items=rendering_targets, label="Render target"
        )

    def _get_reviewable_bool(self):
        return BoolDef(
            "review",
            default=("reviewable" in self.instance_attributes),
            label="Review",
        )

    def _get_image_format_enum(self):
        image_format_options = ["exr", "tga", "tif", "png", "jpg"]
        return EnumDef(
            "image_format",
            items=image_format_options,
            default=self.image_format,
            label="Output Image Format",
        )
