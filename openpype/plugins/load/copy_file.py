from openpype.style import get_default_entity_icon_color
from openpype.pipeline import load


class CopyFile(load.LoaderPlugin):
    """Copy the published file to be pasted at the desired location"""

    representations = ["*"]
    families = ["*"]

    label = "Copy File"
    order = 10
    icon = "copy"
    color = get_default_entity_icon_color()

    def load(self, context, name=None, namespace=None, data=None):
        path = self.filepath_from_context(context)
        self.log.info("Added copy to clipboard: {0}".format(path))
        self.copy_file_to_clipboard(path)

    @staticmethod
    def copy_file_to_clipboard(path):
        from qtpy import QtCore, QtWidgets

        clipboard = QtWidgets.QApplication.clipboard()
        assert clipboard, "Must have running QApplication instance"

        # Build mime data for clipboard
        data = QtCore.QMimeData()
        url = QtCore.QUrl.fromLocalFile(path)
        data.setUrls([url])

        # Set to Clipboard
        clipboard.setMimeData(data)
