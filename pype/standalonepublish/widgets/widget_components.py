from . import QtWidgets, QtCore, QtGui
from . import DropDataFrame

from .. import publish


class ComponentsWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__()
        self.initialized = False
        self.valid_components = False
        self.valid_family = False
        self.valid_repre_names = False

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
        self.btn_publish.clicked.connect(self._publish)
        self.initialized = True

    def validation(self):
        if self.initialized is False:
            return
        valid = (
            self.parent_widget.valid_family and
            self.valid_components and
            self.valid_repre_names
        )
        self.btn_publish.setEnabled(valid)

    def set_valid_components(self, valid):
        self.valid_components = valid
        self.validation()

    def set_valid_repre_names(self, valid):
        self.valid_repre_names = valid
        self.validation()

    def process_mime_data(self, mime_data):
        self.drop_frame.process_ent_mime(mime_data)

    def collect_data(self):
        return self.drop_frame.collect_data()

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

    def working_start(self, msg=None):
        if hasattr(self, 'parent_widget'):
            self.parent_widget.working_start(msg)

    def working_stop(self):
        if hasattr(self, 'parent_widget'):
            self.parent_widget.working_stop()

    def _publish(self):
        self.working_start('Pyblish is running')
        try:
            data = self.parent_widget.collect_data()
            publish.set_context(
                data['project'], data['asset'], data['task'], 'standalonepublish'
            )
            result = publish.publish(data)
            # Clear widgets from components list if publishing was successful
            if result:
                self.drop_frame.components_list.clear_widgets()
                self.drop_frame._refresh_view()
        finally:
            self.working_stop()
