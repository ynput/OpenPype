#! python3
import os
import sys

import opentimelineio as otio

from openpype.pipeline import install_host

from openpype.hosts.resolve import TestGUI
import openpype.hosts.resolve as bmdvr
from openpype.hosts.resolve.otio import davinci_export as otio_export


class ThisTestGUI(TestGUI):
    extensions = [".exr", ".jpg", ".mov", ".png", ".mp4", ".ari", ".arx"]

    def __init__(self):
        super(ThisTestGUI, self).__init__()
        # activate resolve from openpype
        install_host(bmdvr)

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
        edl_path = os.path.join(self.input_dir_path, "this_file_name.edl")
        print(f"_ edl_path: `{edl_path}`")
        # xml_string = otio_adapters.fcpx_xml.write_to_string(otio_timeline)
        # print(f"_ xml_string: `{xml_string}`")
        otio.adapters.write_to_file(
            otio_timeline, edl_path, adapter_name="cmx_3600")
        project = bmdvr.get_current_project()
        media_pool = project.GetMediaPool()
        timeline = media_pool.ImportTimelineFromFile(edl_path)
        # at the end close the window
        self._close_window(None)


if __name__ == "__main__":
    test_gui = ThisTestGUI()
    test_gui.show_gui()
    sys.exit(not bool(True))
