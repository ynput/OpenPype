from . import QtWidgets, QtCore, QtGui
from . import DropDataFrame

class ComponentsWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__()
        body = QtWidgets.QWidget()
        self.parent_widget = parent
        self.drop_frame = DropDataFrame(self)

        buttons = QtWidgets.QWidget()

        layout = QtWidgets.QHBoxLayout(buttons)

        self.btn_browse = QtWidgets.QPushButton('Browse')
        self.btn_browse.setToolTip('Browse for file(s).')
        self.btn_browse.setFocusPolicy(QtCore.Qt.NoFocus)

        self.btn_publish = QtWidgets.QPushButton('Publish')
        self.btn_publish.setToolTip('Publishes data.')
        self.btn_publish.setFocusPolicy(QtCore.Qt.NoFocus)

        layout.addWidget(self.btn_browse, alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(self.btn_publish, alignment=QtCore.Qt.AlignRight)

        layout = QtWidgets.QVBoxLayout(body)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.drop_frame)
        layout.addWidget(buttons)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(body)

        self.btn_browse.clicked.connect(self._browse)

    def set_valid(self, in_bool):
        self.btn_publish.setEnabled(in_bool)

    def set_valid_components(self, in_bool):
        self.parent_widget.set_valid_components(in_bool)

    def process_mime_data(self, mime_data):
        self.drop_frame.process_ent_mime(mime_data)

    def _browse(self):
        options = [
            QtWidgets.QFileDialog.DontResolveSymlinks,
            QtWidgets.QFileDialog.DontUseNativeDialog
        ]
        folders = False
        if folders:
            # browse folders specifics
            caption = "Browse folders to publish image sequences"
            file_mode = QtWidgets.QFileDialog.Directory
            options.append(QtWidgets.QFileDialog.ShowDirsOnly)
        else:
            # browse files specifics
            caption = "Browse files to publish"
            file_mode = QtWidgets.QFileDialog.ExistingFiles

        # create the dialog
        file_dialog = QtWidgets.QFileDialog(parent=self, caption=caption)
        file_dialog.setLabelText(QtWidgets.QFileDialog.Accept, "Select")
        file_dialog.setLabelText(QtWidgets.QFileDialog.Reject, "Cancel")
        file_dialog.setFileMode(file_mode)

        # set the appropriate options
        for option in options:
            file_dialog.setOption(option)

        # browse!
        if not file_dialog.exec_():
            return

        # process the browsed files/folders for publishing
        paths = file_dialog.selectedFiles()
        self.drop_frame._process_paths(paths)
