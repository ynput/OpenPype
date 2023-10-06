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
    Creator as NewCreator,
    CreatedInstance,
    Anatomy
)


class CreateSaver(NewCreator):
    identifier = "io.openpype.creators.fusion.saver"
    label = "Render (saver)"
    name = "render"
    family = "render"
    default_variants = ["Main", "Mask"]
    description = "Fusion Saver to generate image sequence"
    icon = "fa5.eye"

    instance_attributes = [
        "reviewable"
    ]

    # TODO: This should be renamed together with Nuke so it is aligned
    temp_rendering_path_template = (
        "{workdir}/renders/fusion/{subset}/{subset}.{frame}.{ext}")

    def create(self, subset_name, instance_data, pre_create_data):
        self.pass_pre_attributes_to_instance(
            instance_data,
            pre_create_data
        )

        instance_data.update({
            "id": "pyblish.avalon.instance",
            "subset": subset_name
        })

        # TODO: Add pre_create attributes to choose file format?
        file_format = "OpenEXRFormat"

        comp = get_current_comp()
        with comp_lock_and_undo_chunk(comp):
            args = (-32768, -32768)  # Magical position numbers
            saver = comp.AddTool("Saver", *args)

            self._update_tool_with_data(saver, data=instance_data)

            saver["OutputFormat"] = file_format

            # Check file format settings are available
            if saver[file_format] is None:
                raise RuntimeError(
                    f"File format is not set to {file_format}, this is a bug"
                )

            # Set file format attributes
            saver[file_format]["Depth"] = 0  # Auto | float16 | float32
            # TODO Is this needed?
            saver[file_format]["SaveAlpha"] = 1

        self._imprint(saver, instance_data)

        # Register the CreatedInstance
        instance = CreatedInstance(
            family=self.family,
            subset_name=subset_name,
            data=instance_data,
            creator=self,
        )

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
        subset = data["subset"]
        if original_subset != subset:
            self._configure_saver_tool(data, tool, subset)

    def _configure_saver_tool(self, data, tool, subset):
        formatting_data = deepcopy(data)

        # get frame padding from anatomy templates
        anatomy = Anatomy()
        frame_padding = int(
            anatomy.templates["render"].get("frame_padding", 4)
        )

        # Subset change detected
        workdir = os.path.normpath(legacy_io.Session["AVALON_WORKDIR"])
        formatting_data.update({
            "workdir": workdir,
            "frame": "0" * frame_padding,
            "ext": "exr"
        })

        # build file path to render
        filepath = self.temp_rendering_path_template.format(
            **formatting_data)

        tool["Clip"] = os.path.normpath(filepath)

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

    def get_pre_create_attr_defs(self):
        """Settings for create page"""
        attr_defs = [
            self._get_render_target_enum(),
            self._get_reviewable_bool(),
            self._get_frame_range_enum()
        ]
        return attr_defs

    def get_instance_attr_defs(self):
        """Settings for publish page"""
        return self.get_pre_create_attr_defs()

    def pass_pre_attributes_to_instance(
        self,
        instance_data,
        pre_create_data
    ):
        creator_attrs = instance_data["creator_attributes"] = {}
        for pass_key in pre_create_data.keys():
            creator_attrs[pass_key] = pre_create_data[pass_key]

    # These functions below should be moved to another file
    # so it can be used by other plugins. plugin.py ?
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

    def _get_frame_range_enum(self):
        frame_range_options = {
            "asset_db": "Current asset context",
            "render_range": "From render in/out",
            "comp_range": "From composition timeline"
        }

        return EnumDef(
            "frame_range_source",
            items=frame_range_options,
            label="Frame range source"
        )

    def _get_reviewable_bool(self):
        return BoolDef(
            "review",
            default=("reviewable" in self.instance_attributes),
            label="Review",
        )

    def apply_settings(self, project_settings):
        """Method called on initialization of plugin to apply settings."""

        # plugin settings
        plugin_settings = (
            project_settings["fusion"]["create"][self.__class__.__name__]
        )

        # individual attributes
        self.instance_attributes = plugin_settings.get(
            "instance_attributes") or self.instance_attributes
        self.default_variants = plugin_settings.get(
            "default_variants") or self.default_variants
        self.temp_rendering_path_template = (
            plugin_settings.get("temp_rendering_path_template")
            or self.temp_rendering_path_template
        )
