# -*- coding: utf-8 -*-
"""Editor for shader definitions.

Shader names are stored as simple text file over GridFS in mongodb.

"""
import os
from Qt import QtWidgets, QtCore, QtGui
from openpype.lib.mongo import OpenPypeMongoConnection
from openpype import resources
import gridfs


DEFINITION_FILENAME = "{}/maya/shader_definition.txt".format(
    os.getenv("AVALON_PROJECT"))


class ShaderDefinitionsEditor(QtWidgets.QWidget):
    """Widget serving as simple editor for shader name definitions."""

    # name of the file used to store definitions

    def __init__(self, parent=None):
        super(ShaderDefinitionsEditor, self).__init__(parent)
        self._mongo = OpenPypeMongoConnection.get_mongo_client()
        self._gridfs = gridfs.GridFS(
            self._mongo[os.getenv("OPENPYPE_DATABASE_NAME")])
        self._editor = None

        self._original_content = self._read_definition_file()

        self.setObjectName("shaderDefinitionEditor")
        self.setWindowTitle("OpenPype shader name definition editor")
        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
        self.setWindowIcon(icon)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setParent(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.resize(750, 500)

        self._setup_ui()
        self._reload()

    def _setup_ui(self):
        """Setup UI of Widget."""
        layout = QtWidgets.QVBoxLayout(self)
        label = QtWidgets.QLabel()
        label.setText("Put shader names here - one name per line:")
        layout.addWidget(label)
        self._editor = QtWidgets.QPlainTextEdit()
        self._editor.setStyleSheet("border: none;")
        layout.addWidget(self._editor)

        btn_layout = QtWidgets.QHBoxLayout()
        save_btn = QtWidgets.QPushButton("Save")
        save_btn.clicked.connect(self._save)

        reload_btn = QtWidgets.QPushButton("Reload")
        reload_btn.clicked.connect(self._reload)

        exit_btn = QtWidgets.QPushButton("Exit")
        exit_btn.clicked.connect(self._close)

        btn_layout.addWidget(reload_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(exit_btn)

        layout.addLayout(btn_layout)

    def _read_definition_file(self, file=None):
        """Read definition file from database.

        Args:
            file (gridfs.grid_file.GridOut, Optional): File to read. If not
                set, new query will be issued to find it.

        Returns:
            str: Content of the file or empty string if file doesn't exist.

        """
        content = ""
        if not file:
            file = self._gridfs.find_one(
                {"filename": DEFINITION_FILENAME})
        if not file:
            print(">>> [SNDE]: nothing in database yet")
            return content
        content = file.read()
        file.close()
        return content

    def _write_definition_file(self, content, force=False):
        """Write content as definition to file in database.

        Before file is written, check is made if its content has not
        changed. If is changed, warning is issued to user if he wants
        it to overwrite. Note: GridFs doesn't allow changing file content.
        You need to delete existing file and create new one.

        Args:
            content (str): Content to write.

        Raises:
            ContentException: If file is changed in database while
                editor is running.
        """
        file = self._gridfs.find_one(
            {"filename": DEFINITION_FILENAME})
        if file:
            content_check = self._read_definition_file(file)
            if content == content_check:
                print(">>> [SNDE]: content not changed")
                return
            if self._original_content != content_check:
                if not force:
                    raise ContentException("Content changed")
            print(">>> [SNDE]: overwriting data")
            file.close()
            self._gridfs.delete(file._id)

        file = self._gridfs.new_file(
            filename=DEFINITION_FILENAME,
            content_type='text/plain',
            encoding='utf-8')
        file.write(content)
        file.close()
        QtCore.QTimer.singleShot(200, self._reset_style)
        self._editor.setStyleSheet("border: 1px solid #33AF65;")
        self._original_content = content

    def _reset_style(self):
        """Reset editor style back.

        Used to visually indicate save.

        """
        self._editor.setStyleSheet("border: none;")

    def _close(self):
        self.hide()

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def _reload(self):
        print(">>> [SNDE]: reloading")
        self._set_content(self._read_definition_file())

    def _save(self):
        try:
            self._write_definition_file(content=self._editor.toPlainText())
        except ContentException:
            # content has changed meanwhile
            print(">>> [SNDE]: content has changed")
            self._show_overwrite_warning()

    def _set_content(self, content):
        self._editor.setPlainText(content)

    def _show_overwrite_warning(self):
        reply = QtWidgets.QMessageBox.question(
            self,
            "Warning",
            ("Content you are editing was changed meanwhile in database.\n"
             "Please, reload and solve the conflict."),
            QtWidgets.QMessageBox.OK)

        if reply == QtWidgets.QMessageBox.OK:
            # do nothing
            pass


class ContentException(Exception):
    """This is risen during save if file is changed in database."""
    pass
