#! python3
import os
import sys
import avalon.api as avalon
import pype
import opentimelineio as otio
from opentimelineio_contrib import adapters as otio_adapters
from pype.hosts.resolve import TestGUI
import pype.hosts.resolve as bmdvr
from pype.hosts.resolve.otio import davinci_export as otio_export


class ThisTestGUI(TestGUI):
    extensions = [".exr", ".jpg", ".mov", ".png", ".mp4", ".ari", ".arx"]

    def __init__(self):
        super(ThisTestGUI, self).__init__()
        # Registers pype's Global pyblish plugins
        pype.install()
        # activate resolve from pype
        avalon.install(bmdvr)

    def _open_dir_button_pressed(self, event):
        # selected_path = self.fu.RequestFile(os.path.expanduser("~"))
        selected_path = self.fu.RequestDir(os.path.expanduser("~"))
        self._widgets["inputTestSourcesFolder"].Text = selected_path

    # main function
    def process(self, event):
        self.input_dir_path = self._widgets["inputTestSourcesFolder"].Text
        project = bmdvr.get_current_project()
        otio_timeline = otio_export.create_otio_timeline(project)
        print(f"_ otio_timeline: `{otio_timeline}`")
        aaf_path = os.path.join(self.input_dir_path, "this_file_name.aaf")
        print(f"_ aaf_path: `{aaf_path}`")
        # xml_string = otio_adapters.fcpx_xml.write_to_string(otio_timeline)
        # print(f"_ xml_string: `{xml_string}`")
        otio.adapters.write_to_file(
            otio_timeline, aaf_path, adapter_name="AAF")
        # at the end close the window
        self._close_window(None)


if __name__ == "__main__":
    test_gui = ThisTestGUI()
    test_gui.show_gui()
    sys.exit(not bool(True))
