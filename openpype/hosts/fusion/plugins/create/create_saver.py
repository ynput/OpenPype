import os

import qtawesome

from openpype.hosts.fusion.api import (
    get_current_comp,
    comp_lock_and_undo_chunk
)

from openpype.pipeline import (
    legacy_io,
    Creator,
    CreatedInstance
)


class CreateSaver(Creator):
    identifier = "io.openpype.creators.fusion.saver"
    name = "saver"
    label = "Saver"
    family = "render"
    default_variants = ["Main"]

    description = "Fusion Saver to generate image sequence"

    def create(self, subset_name, instance_data, pre_create_data):

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
                raise RuntimeError("File format is not set to {}, "
                                   "this is a bug".format(file_format))

            # Set file format attributes
            saver[file_format]["Depth"] = 1  # int8 | int16 | float32 | other
            saver[file_format]["SaveAlpha"] = 0

        self._imprint(saver, instance_data)

        # Register the CreatedInstance
        instance = CreatedInstance(
            family=self.family,
            subset_name=subset_name,
            data=instance_data,
            creator=self)

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
                data = self._collect_unmanaged_saver(tool)

            # Add instance
            created_instance = CreatedInstance.from_existing(data, self)

            # Collect transient data
            created_instance.transient_data["tool"] = tool

            self._add_instance_to_context(created_instance)

    def get_icon(self):
        return qtawesome.icon("fa.eye", color="white")

    def update_instances(self, update_list):
        for update in update_list:
            instance = update.instance

            # Get the new values after the changes by key, ignore old value
            new_data = {
                key: new for key, (_old, new) in update.changes.items()
            }

            tool = instance.transient_data["tool"]
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
        for key, value in data.items():
            tool.SetData("openpype.{}".format(key), value)

    def _update_tool_with_data(self, tool, data):
        """Update tool node name and output path based on subset data"""
        if "subset" not in data:
            return

        original_subset = tool.GetData("openpype.subset")
        subset = data["subset"]
        if original_subset != subset:
            # Subset change detected
            # Update output filepath
            workdir = os.path.normpath(legacy_io.Session["AVALON_WORKDIR"])
            filename = "{}..exr".format(subset)
            filepath = os.path.join(workdir, "render", subset, filename)
            tool["Clip"] = filepath

            # Rename tool
            if tool.Name != subset:
                print(f"Renaming {tool.Name} -> {subset}")
                tool.SetAttrs({"TOOLS_Name": subset})

    def _collect_unmanaged_saver(self, tool):

        # TODO: this should not be done this way - this should actually
        #       get the data as stored on the tool explicitly (however)
        #       that would disallow any 'regular saver' to be collected
        #       unless the instance data is stored on it to begin with

        print("Collecting unmanaged saver..")
        comp = tool.Comp()

        # Allow regular non-managed savers to also be picked up
        project = legacy_io.Session["AVALON_PROJECT"]
        asset = legacy_io.Session["AVALON_ASSET"]
        task = legacy_io.Session["AVALON_TASK"]

        path = tool["Clip"][comp.TIME_UNDEFINED]
        fname = os.path.basename(path)
        fname, _ext = os.path.splitext(fname)
        subset = fname.rstrip(".")

        attrs = tool.GetAttrs()
        passthrough = attrs["TOOLB_PassThrough"]
        variant = subset[len("render"):]
        return {
            # Required data
            "project": project,
            "asset": asset,
            "subset": subset,
            "task": task,
            "variant": variant,
            "active": not passthrough,
            "family": self.family,

            # Unique identifier for instance and this creator
            "id": "pyblish.avalon.instance",
            "creator_identifier": self.identifier
        }

    def get_managed_tool_data(self, tool):
        """Return data of the tool if it matches creator identifier"""
        data = tool.GetData('openpype')
        if not isinstance(data, dict):
            return

        required = {
            "id": "pyblish.avalon.instance",
            "creator_identifier": self.identifier
        }
        for key, value in required.items():
            if key not in data or data[key] != value:
                return

        return data
