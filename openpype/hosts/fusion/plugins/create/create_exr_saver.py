import os

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
    default_variants  = ["Main"]

    selected_nodes = []

    def create(self, subset_name, instance_data, pre_create_data):

        file_format = "OpenEXRFormat"

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

    def collect_instances(self):
        for instance in list_instances(creator_id=self.identifier):
            created_instance = CreatedInstance.from_existing(instance, self)
            self._add_instance_to_context(created_instance)

    def update_instances(self, update_list):
        print(update_list)

    def remove_instances(self, instances):
        for instance in instances:
            remove_instance(instance)

    def get_pre_create_attr_defs(self):
        return []
