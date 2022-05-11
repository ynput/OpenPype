import os

from openpype.pipeline import LegacyCreator
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

        # todo: improve method of getting current environment
        # todo: pref avalon.Session over os.environ

        workdir = os.path.normpath(os.environ["AVALON_WORKDIR"])

        filename = "{}..tiff".format(self.name)
        filepath = os.path.join(workdir, "render", filename)

        with comp_lock_and_undo_chunk(comp):
            args = (-32768, -32768)  # Magical position numbers
            saver = comp.AddTool("Saver", *args)
            saver.SetAttrs({"TOOLS_Name": self.name})

            # Setting input attributes is different from basic attributes
            # Not confused with "MainInputAttributes" which
            saver["Clip"] = filepath
            saver["OutputFormat"] = file_format

            # # # Set standard TIFF settings
            if saver[file_format] is None:
                raise RuntimeError("File format is not set to TiffFormat, "
                                   "this is a bug")

            # Set file format attributes
            saver[file_format]["Depth"] = 1  # int8 | int16 | float32 | other
            saver[file_format]["SaveAlpha"] = 0
