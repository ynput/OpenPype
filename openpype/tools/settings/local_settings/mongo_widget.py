import os
import sys
import traceback

from Qt import QtWidgets
from pymongo.errors import ServerSelectionTimeoutError

from openpype.api import change_openpype_mongo_url
from openpype.tools.utils import PlaceholderLineEdit


class OpenPypeMongoWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(OpenPypeMongoWidget, self).__init__(parent)

        # Warning label
        warning_label = QtWidgets.QLabel((
            "WARNING: Requires restart. Change of OpenPype Mongo requires to"
            " restart of all running Pype processes and process using Pype"
            " (Including this)."
            "\n- all changes in different categories won't be saved."
        ), self)
        warning_label.setStyleSheet("font-weight: bold;")

        # Label
        mongo_url_label = QtWidgets.QLabel("OpenPype Mongo URL", self)

        # Input
        mongo_url_input = PlaceholderLineEdit(self)
        mongo_url_input.setPlaceholderText("< OpenPype Mongo URL >")
        mongo_url_input.setText(os.environ["OPENPYPE_MONGO"])

        # Confirm button
        mongo_url_change_btn = QtWidgets.QPushButton("Confirm Change", self)

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(warning_label, 0, 0, 1, 3)
        layout.addWidget(mongo_url_label, 1, 0)
        layout.addWidget(mongo_url_input, 1, 1)
        layout.addWidget(mongo_url_change_btn, 1, 2)

        mongo_url_change_btn.clicked.connect(self._on_confirm_click)

        self.mongo_url_input = mongo_url_input

    def _on_confirm_click(self):
        value = self.mongo_url_input.text()

        dialog = QtWidgets.QMessageBox(self)

        title = "OpenPype mongo changed"
        message = (
            "OpenPype mongo url was successfully changed."
            " Restart OpenPype application please."
        )
        details = None

        try:
            change_openpype_mongo_url(value)
        except Exception as exc:
            if isinstance(exc, ServerSelectionTimeoutError):
                error_message = (
                    "Connection timeout passed."
                    " Probably can't connect to the Mongo server."
                )
            else:
                error_message = str(exc)

            title = "OpenPype mongo change failed"
            # TODO catch exception message more gracefully
            message = (
                "OpenPype mongo change was not successful."
                " Full traceback can be found in details section.\n\n"
                "Error message:\n{}"
            ).format(error_message)
            details = "\n".join(traceback.format_exception(*sys.exc_info()))
        dialog.setWindowTitle(title)
        dialog.setText(message)
        if details:
            dialog.setDetailedText(details)
        dialog.exec_()
