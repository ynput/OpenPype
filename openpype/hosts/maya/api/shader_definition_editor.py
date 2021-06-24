# -*- coding: utf-8 -*-
"""Editor for shader definitions."""
import os
import csv
from Qt import QtWidgets, QtCore, QtGui
from openpype.lib.mongo import OpenPypeMongoConnection
from openpype import resources
import gridfs


class ShaderDefinitionsEditor(QtWidgets.QWidget):

    DEFINITION_FILENAME = "maya/shader_definition.csv"

    def __init__(self, parent=None):
        super(ShaderDefinitionsEditor, self).__init__(parent)
        self._mongo = OpenPypeMongoConnection.get_mongo_client()
        self._gridfs = gridfs.GridFS( self._mongo[os.getenv("OPENPYPE_DATABASE_NAME")])

        # TODO: handle GridIn and GridOut
        self._file = self._gridfs.find_one(
            {"filename": self.DEFINITION_FILENAME})
        if not self._file:
            self._file = self._gridfs.new_file(filename=self.DEFINITION_FILENAME)

        self.setObjectName("shaderDefinitionEditor")
        self.setWindowTitle("OpenPype shader definition editor")
        icon = QtGui.QIcon(resources.pype_icon_filepath())
        self.setWindowIcon(icon)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setParent(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.resize(750, 500)

        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        self._editor = QtWidgets.QPlainTextEdit()
        layout.addWidget(self._editor)

        btn_layout = QtWidgets.QHBoxLayout()
        save_btn = QtWidgets.QPushButton("Save")
        save_btn.clicked.connect(self._close)

        reload_btn = QtWidgets.QPushButton("Reload")
        reload_btn.clicked.connect(self._reload)

        exit_btn = QtWidgets.QPushButton("Exit")
        exit_btn.clicked.connect(self._close)

        btn_layout.addWidget(reload_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(exit_btn)

        layout.addLayout(btn_layout)

    def _read_definition_file(self):
        content = []
        with open(self._file, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                content.append(row)

        return content

    def _write_definition_file(self, content):
        with open(self._file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(content.splitlines())

    def _close(self):
        self.close()

    def _reload(self):
        print("reloading")
        self._set_content(self._read_definition_file())

    def _save(self):
        pass

    def _set_content(self, content):
        self._editor.set_content("\n".join(content))
