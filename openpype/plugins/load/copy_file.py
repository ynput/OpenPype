from avalon import style

from openpype.pipeline import load


class CopyFile(load.LoaderPlugin):
    """Copy the published file to be pasted at the desired location"""

    representations = ["*"]
    families = ["*"]

    label = "Copy File"
    order = 10
    icon = "copy"
    color = style.colors.default

    def load(self, context, name=None, namespace=None, data=None):
        self.log.info("Added copy to clipboard: {0}".format(self.fname))
        self.copy_file_to_clipboard(self.fname)

    @staticmethod
    def copy_file_to_clipboard(path):
        from Qt import QtCore, QtWidgets

        clipboard = QtWidgets.QApplication.clipboard()
        assert clipboard, "Must have running QApplication instance"

        # Build mime data for clipboard
        data = QtCore.QMimeData()
        url = QtCore.QUrl.fromLocalFile(path)
        data.setUrls([url])

        # Set to Clipboard
        clipboard.setMimeData(data)
