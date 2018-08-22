from avalon import api, style


class CopyFile(api.Loader):
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
        from avalon.vendor.Qt import QtCore, QtWidgets

        app = QtWidgets.QApplication.instance()
        assert app, "Must have running QApplication instance"

        # Build mime data for clipboard
        file_path = QtCore.QUrl.fromLocalFile(path)
        byte_array = QtCore.QByteArray("copy\n").append(file_path)

        mime = QtCore.QMimeData()
        mime.setData("text/uri-list", byte_array)

        # Set to Clipboard
        clipboard = app.clipboard()
        clipboard.setMimeData(mime)