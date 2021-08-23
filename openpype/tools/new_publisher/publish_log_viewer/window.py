import os
import sys
import json
import copy
import uuid
import collections

openpype_dir = r"C:\Users\jakub.trllo\Desktop\pype\pype3"
mongo_url = "mongodb://localhost:2707"

os.environ["OPENPYPE_MONGO"] = mongo_url
os.environ["AVALON_MONGO"] = mongo_url
os.environ["OPENPYPE_DATABASE_NAME"] = "openpype"
os.environ["AVALON_CONFIG"] = "openpype"
os.environ["AVALON_TIMEOUT"] = "1000"
os.environ["AVALON_DB"] = "avalon"
for path in [
    openpype_dir,
    r"{}\repos\avalon-core".format(openpype_dir),
    r"{}\.venv\Lib\site-packages".format(openpype_dir)
]:
    sys.path.append(path)

from Qt import QtWidgets, QtCore, QtGui

from openpype import style
if __package__:
    from .widgets import PublishLogViewerWidget
else:
    from widgets import PublishLogViewerWidget


class PublishLogViewerWindow(QtWidgets.QWidget):
    # TODO add buttons to be able load report file or paste content of report
    default_width = 1200
    default_height = 600

    def __init__(self, parent=None):
        super(PublishLogViewerWindow, self).__init__(parent)

        main_widget = PublishLogViewerWidget(self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(main_widget)

        self._main_widget = main_widget

        self.resize(self.default_width, self.default_height)
        self.setStyleSheet(style.load_stylesheet())

    def set_report(self, report_data):
        self._main_widget.set_report(report_data)


def main():
    """Main function for testing purposes."""
    app = QtWidgets.QApplication([])
    window = PublishLogViewerWindow()

    log_path = os.path.join(os.path.dirname(__file__), "logs.json")
    with open(log_path, "r") as file_stream:
        report_data = json.load(file_stream)

    window.set_report(report_data)

    window.show()
    app.exec_()


if __name__ == "__main__":
    main()
