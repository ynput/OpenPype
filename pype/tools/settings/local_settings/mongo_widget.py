import os
import sys
import traceback

from Qt import QtWidgets
from pymongo.errors import ServerSelectionTimeoutError

from pype.api import change_pype_mongo_url


class PypeMongoWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(PypeMongoWidget, self).__init__(parent)

        # Warning label
        warning_label = QtWidgets.QLabel((
            "WARNING: Requires restart. Change of Pype Mongo requires to"
            " restart of all running Pype processes and process using Pype"
            " (Including this)."
            "\n- all changes in different categories won't be saved."
        ), self)
        warning_label.setStyleSheet("font-weight: bold;")

        # Label
        mongo_url_label = QtWidgets.QLabel("Pype Mongo URL", self)

        # Input
        mongo_url_input = QtWidgets.QLineEdit(self)
        mongo_url_input.setPlaceholderText("< Pype Mongo URL >")
        mongo_url_input.setText(os.environ["PYPE_MONGO"])

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

        title = "Pype mongo changed"
        message = (
            "Pype mongo url was successfully changed. Restart Pype please."
        )
        details = None

        try:
            change_pype_mongo_url(value)
        except Exception as exc:
            if isinstance(exc, ServerSelectionTimeoutError):
                error_message = (
                    "Connection timeout passed."
                    " Probably can't connect to the Mongo server."
                )
            else:
                error_message = str(exc)

            title = "Pype mongo change failed"
            # TODO catch exception message more gracefully
            message = (
                "Pype mongo change was not successful."
                " Full traceback can be found in details section.\n\n"
                "Error message:\n{}"
            ).format(error_message)
            details = "\n".join(traceback.format_exception(*sys.exc_info()))
        dialog.setWindowTitle(title)
        dialog.setText(message)
        if details:
            dialog.setDetailedText(details)
        dialog.exec_()
