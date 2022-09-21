import os

import qtawesome

from openpype.hosts.fusion.api import (
    get_current_comp,
    comp_lock_and_undo_chunk,
    remove_instance,
    list_instances
)

from openpype.pipeline import (
    legacy_io,
    Creator,
    CreatedInstance
)


class CreateOpenEXRSaver(Creator):
    identifier = "io.openpype.creators.fusion.saver"
    name = "openexrDefault"
    label = "Create OpenEXR Saver"
    family = "render"
    default_variants = ["Main"]

    description = "Fusion Saver to generate EXR image sequence"

    selected_nodes = []

    def create(self, subset_name, instance_data, pre_create_data):

        file_format = "OpenEXRFormat"

        print(subset_name)
        print(instance_data)
        print(pre_create_data)

        comp = get_current_comp()

        workdir = os.path.normpath(legacy_io.Session["AVALON_WORKDIR"])

        filename = "{}..exr".format(subset_name)
        filepath = os.path.join(workdir, "render", filename)

        with comp_lock_and_undo_chunk(comp):
            args = (-32768, -32768)  # Magical position numbers
            saver = comp.AddTool("Saver", *args)
            saver.SetAttrs({"TOOLS_Name": subset_name})

            # Setting input attributes is different from basic attributes
            # Not confused with "MainInputAttributes" which
            saver["Clip"] = filepath
            saver["OutputFormat"] = file_format

            # Check file format settings are available
            if saver[file_format] is None:
                raise RuntimeError("File format is not set to {}, "
                                   "this is a bug".format(file_format))

            # Set file format attributes
            saver[file_format]["Depth"] = 1  # int8 | int16 | float32 | other
            saver[file_format]["SaveAlpha"] = 0

        # Save all data in a "openpype.{key}" = value data
        for key, value in instance_data.items():
            saver.SetData("openpype.{}".format(key), value)

    def collect_instances(self):

        comp = get_current_comp()
        tools = comp.GetToolList(False, "Saver").values()

        # Allow regular non-managed savers to also be picked up
        project = legacy_io.Session["AVALON_PROJECT"]
        asset = legacy_io.Session["AVALON_ASSET"]
        task = legacy_io.Session["AVALON_TASK"]

        for tool in tools:

            path = tool["Clip"][comp.TIME_UNDEFINED]
            fname = os.path.basename(path)
            fname, _ext = os.path.splitext(fname)
            subset = fname.rstrip(".")

            attrs = tool.GetAttrs()
            passthrough = attrs["TOOLB_PassThrough"]
            variant = subset[len("render"):]

            # TODO: this should not be done this way - this should actually
            #       get the data as stored on the tool explicitly (however)
            #       that would disallow any 'regular saver' to be collected
            #       unless the instance data is stored on it to begin with
            instance = {
                # Required data
                "project": project,
                "asset": asset,
                "subset": subset,
                "task": task,
                "variant": variant,
                "active": not passthrough,
                "family": self.family,

                # Fusion data
                "tool_name": tool.Name
            }

            # Use the explicit data on the saver (if any)
            data = tool.GetData("openpype")
            if data:
                instance.update(data)

            # Add instance
            created_instance = CreatedInstance.from_existing(instance, self)

            # TODO: move this to lifetime data or alike
            #       (Doing this before CreatedInstance.from_existing wouldn't
            #        work because `tool` isn't JSON serializable)
            created_instance["tool"] = tool

            self._add_instance_to_context(created_instance)

    def get_icon(self):
        return qtawesome.icon("fa.eye", color="white")

    def update_instances(self, update_list):
        # TODO: Not sure what to do here?
        print(update_list)

    def remove_instances(self, instances):
        for instance in instances:

            # Remove the tool from the scene
            remove_instance(instance)

            # Remove the collected CreatedInstance to remove from UI directly
            self._remove_instance_from_context(instance)

    def get_pre_create_attr_defs(self):
        return []
