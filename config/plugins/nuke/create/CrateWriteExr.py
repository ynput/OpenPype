import os
import sys
import avalon.api
import avalon.nuke


class CrateWriteExr(avalon.api.Creator):
    name = "Write_exr"
    label = "Create Write: exr"
    hosts = ["nuke"]
    family = "studio.write"
    icon = "sign-out"

    # def __init__(self, *args, **kwargs):
    #     super(CrateWriteExr, self).__init__(*args, **kwargs)
    #     self.data.setdefault("subset", "this")

    def process(self):
        nuke = getattr(sys.modules["__main__"], "nuke", None)
        data = {}
        ext = "exr"
        root, nodes = avalon.nuke.get_current_script(nuke=nuke)

        # todo: improve method of getting current environment
        # todo: pref avalon.Session over os.environ

        workdir = os.path.normpath(os.environ["AVALON_WORKDIR"])

        filename = "{}.####.exr".format(self.name)
        filepath = os.path.join(
            workdir,
            "render",
            ext,
            filename
        ).replace("\\", "/")

        with avalon.nuke.viewer_update_and_undo_stop(nuke):
            w = nuke.createNode(
                "Write",
                "name {}".format(self.name))
            # w.knob('colorspace').setValue()
            w.knob('file').setValue(filepath)
            w.knob('file_type').setValue(ext)
            w.knob('datatype').setValue("16 bit half")
            w.knob('compression').setValue("Zip (1 scanline)")
            w.knob('create_directories').setValue(True)
            w.knob('autocrop').setValue(True)

        return data
