#! python3
import os
import sys

from openpype.pipeline import install_host
from openpype.hosts.resolve import TestGUI
import openpype.hosts.resolve as bmdvr
import clique


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

        self.dir_processing(self.input_dir_path)

        # at the end close the window
        self._close_window(None)

    def dir_processing(self, dir_path):
        collections, reminders = clique.assemble(os.listdir(dir_path))

        # process reminders
        for _rem in reminders:
            _rem_path = os.path.join(dir_path, _rem)

            # go deeper if directory
            if os.path.isdir(_rem_path):
                print(_rem_path)
                self.dir_processing(_rem_path)
            else:
                self.file_processing(_rem_path)

        # process collections
        for _coll in collections:
            _coll_path = os.path.join(dir_path, list(_coll).pop())
            self.file_processing(_coll_path)

    def file_processing(self, fpath):
        print(f"_ fpath: `{fpath}`")
        _base, ext = os.path.splitext(fpath)
        # skip if unwanted extension
        if ext not in self.extensions:
            return
        media_pool_item = bmdvr.create_media_pool_item(fpath)
        print(media_pool_item)

        track_item = bmdvr.create_timeline_item(media_pool_item)
        print(track_item)


if __name__ == "__main__":
    test_gui = ThisTestGUI()
    test_gui.show_gui()
    sys.exit(not bool(True))
