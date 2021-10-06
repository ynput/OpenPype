from Qt import QtWidgets

from .lib import RegisteredRoots
from openpype.tools.loader.widgets import SubsetWidget


class LibrarySubsetWidget(SubsetWidget):
    def on_copy_source(self):
        """Copy formatted source path to clipboard"""
        source = self.data.get("source", None)
        if not source:
            return

        project_name = self.dbcon.Session["AVALON_PROJECT"]
        root = RegisteredRoots.registered_root(project_name)
        path = source.format(root=root)
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(path)
