import os

from openpype.pipeline import (
    LegacyCreator,
    legacy_io
)
from openpype.hosts.fusion.api import (
    get_current_comp,
    comp_lock_and_undo_chunk
)


class CreateOpenEXRSaver(LegacyCreator):

    name = "openexrDefault"
    label = "Create OpenEXR Saver"
    hosts = ["fusion"]
    family = "render"
    defaults = ["Main"]

    def process(self):

        file_format = "OpenEXRFormat"

        comp = get_current_comp()

        workdir = os.path.normpath(legacy_io.Session["AVALON_WORKDIR"])

        filename = "{}..exr".format(self.name)
        filepath = os.path.join(workdir, "render", filename)

        with comp_lock_and_undo_chunk(comp):
            args = (-32768, -32768)  # Magical position numbers
            saver = comp.AddTool("Saver", *args)
            saver.SetAttrs({"TOOLS_Name": self.name})

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
