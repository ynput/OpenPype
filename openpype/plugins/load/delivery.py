import collections
import os
import copy

from avalon import api, style
from avalon.vendor.Qt import QtWidgets, QtCore, QtGui
from avalon.api import AvalonMongoDB
from openpype.api import Anatomy, config
from openpype import resources
from openpype.api import get_anatomy_settings

from openpype.lib.delivery import (
    sizeof_fmt,
    path_from_represenation,
    get_format_dict,
    check_destination_path,
    process_single_file,
    process_sequence,
    report
)


class Delivery(api.SubsetLoader):
    """Export selected versions to folder structure from Template"""

    is_multiple_contexts_compatible = True
    sequence_splitter = "__sequence_splitter__"

    representations = ["*"]
    families = ["*"]
    tool_names = ["library_loader"]

    label = "Deliver Versions"
    order = 35
    icon = "upload"
    color = "#d8d8d8"

    def message(self, text):
        msgBox = QtWidgets.QMessageBox()
        msgBox.setText(text)
        msgBox.setStyleSheet(style.load_stylesheet())
        msgBox.setWindowFlags(
            msgBox.windowFlags() | QtCore.Qt.FramelessWindowHint
        )
        msgBox.exec_()

    def load(self, contexts, name=None, namespace=None, options=None):
        try:
            dialog = DeliveryOptionsDialog(contexts, self.log)
            dialog.exec_()
        except Exception:
            self.log.error("Failed to deliver versions.", exc_info=True)


class DeliveryOptionsDialog(QtWidgets.QDialog):
    """Dialog to select template where to deliver selected representations."""
    SIZE_W = 950
    SIZE_H = 350

    def __init__(self, contexts, log=None, parent=None):
        super(DeliveryOptionsDialog, self).__init__(parent=parent)

        self.project = contexts[0]["project"]["name"]
        self._representations = None
        self.log = log
        self.currently_uploaded = 0

        self.dbcon = AvalonMongoDB()
        self.dbcon.Session["AVALON_PROJECT"] = self.project
        self.dbcon.install()

        self._set_representations(contexts)

        self.setWindowTitle("OpenPype - Deliver versions")
        icon = QtGui.QIcon(resources.pype_icon_filepath())
        self.setWindowIcon(icon)

        self.setWindowFlags(
            QtCore.Qt.WindowCloseButtonHint |
            QtCore.Qt.WindowMinimizeButtonHint
        )
        self.setStyleSheet(style.load_stylesheet())
        self.setMinimumSize(QtCore.QSize(self.SIZE_W, self.SIZE_H))

        layout = QtWidgets.QVBoxLayout()

        input_layout = QtWidgets.QFormLayout()
        input_layout.setContentsMargins(10, 15, 5, 5)

        dropdown = QtWidgets.QComboBox()
        self.templates = self._get_templates(self.project)
        for name, _ in self.templates.items():
            dropdown.addItem(name)

        template_label = QtWidgets.QLabel()
        template_label.setCursor(QtGui.QCursor(QtCore.Qt.IBeamCursor))
        template_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        root_line_edit = QtWidgets.QLineEdit()

        repre_checkboxes_layout = QtWidgets.QFormLayout()
        repre_checkboxes_layout.setContentsMargins(10, 5, 5, 20)

        self._representation_checkboxes = {}
        for repre in self._get_representation_names():
            checkbox = QtWidgets.QCheckBox()
            checkbox.setChecked(True)
            self._representation_checkboxes[repre] = checkbox

            checkbox.stateChanged.connect(self._update_selected_label)
            repre_checkboxes_layout.addRow(repre, checkbox)

        selected_label = QtWidgets.QLabel()

        input_layout.addRow("Selected representations", selected_label)
        input_layout.addRow("Delivery template", dropdown)
        input_layout.addRow("Template value", template_label)
        input_layout.addRow("Root", root_line_edit)
        input_layout.addRow("Representations", repre_checkboxes_layout)

        btn_delivery = QtWidgets.QPushButton("Deliver")
        btn_delivery.setEnabled(bool(dropdown.currentText()))

        progress_bar = QtWidgets.QProgressBar(self)
        progress_bar.setMinimum = 0
        progress_bar.setMaximum = 100
        progress_bar.hide()

        text_area = QtWidgets.QTextEdit()
        text_area.setReadOnly(True)
        text_area.hide()
        text_area.setMinimumHeight(100)

        layout.addLayout(input_layout)
        layout.addWidget(btn_delivery)
        layout.addWidget(progress_bar)
        layout.addWidget(text_area)

        self.setLayout(layout)

        self.selected_label = selected_label
        self.template_label = template_label
        self.dropdown = dropdown
        self.root_line_edit = root_line_edit
        self.progress_bar = progress_bar
        self.text_area = text_area
        self.btn_delivery = btn_delivery

        self.files_selected, self.size_selected = \
            self._get_counts(self._get_selected_repres())

        self._update_selected_label()
        self._update_template_value()

        btn_delivery.clicked.connect(self.deliver)
        dropdown.currentIndexChanged.connect(self._update_template_value)

    def deliver(self):
        """Main method to loop through all selected representations"""
        self.progress_bar.show()
        self.btn_delivery.setEnabled(False)
        # self.resize(self.width(), self.height() + 50)

        report_items = collections.defaultdict(list)

        selected_repres = self._get_selected_repres()
        anatomy = Anatomy(self.project)
        datetime_data = config.get_datetime_data()
        template_name = self.dropdown.currentText()
        format_dict = get_format_dict(anatomy, self.root_line_edit.text())
        for repre in self._representations:
            if repre["name"] not in selected_repres:
                continue

            repre_path = path_from_represenation(repre, anatomy)

            anatomy_data = copy.deepcopy(repre["context"])
            new_report_items = check_destination_path(str(repre["_id"]),
                                                      anatomy,
                                                      anatomy_data,
                                                      datetime_data,
                                                      template_name)

            report_items.update(new_report_items)
            if new_report_items:
                continue

            args = [
                repre_path,
                repre,
                anatomy,
                template_name,
                anatomy_data,
                format_dict,
                report_items,
                self.log
            ]

            if repre.get("files"):
                for repre_file in repre["files"]:
                    src_path = anatomy.fill_root(repre_file["path"])
                    args[0] = src_path
                    new_report_items, uploaded = process_single_file(*args)
                    report_items.update(new_report_items)
                    self._update_progress(uploaded)
            else:  # fallback for Pype2 and representations without files
                frame = repre['context'].get('frame')
                if frame:
                    repre["context"]["frame"] = len(str(frame)) * "#"

                if not frame:
                    new_report_items, uploaded = process_single_file(*args)
                else:
                    new_report_items, uploaded = process_sequence(*args)
                report_items.update(new_report_items)
                self._update_progress(uploaded)

        self.text_area.setText(self._format_report(report(report_items),
                                                   report_items))
        self.text_area.show()

        self.resize(self.width(), self.height() + 125)

    def _get_representation_names(self):
        """Get set of representation names for checkbox filtering."""
        return set([repre["name"] for repre in self._representations])

    def _get_templates(self, project_name):
        """Adds list of delivery templates from Anatomy to dropdown."""
        settings = get_anatomy_settings(project_name)
        templates = {}
        for template_name, value in settings["templates"]["delivery"].items():
            templates[template_name] = value

        return templates

    def _set_representations(self, contexts):
        version_ids = [context["version"]["_id"] for context in contexts]

        repres = list(self.dbcon.find({
            "type": "representation",
            "parent": {"$in": version_ids}
        }))

        self._representations = repres

    def _get_counts(self, selected_repres=None):
        """Returns tuple of number of selected files and their size."""
        files_selected = 0
        size_selected = 0
        for repre in self._representations:
            if repre["name"] in selected_repres:
                for repre_file in repre.get("files", []):

                    files_selected += 1
                    size_selected += repre_file["size"]

        return files_selected, size_selected

    def _prepare_label(self):
        """Provides text with no of selected files and their size."""
        label = "{} files, size {}".format(self.files_selected,
                                           sizeof_fmt(self.size_selected))
        return label

    def _get_selected_repres(self):
        """Returns list of representation names filtered from checkboxes."""
        selected_repres = []
        for repre_name, chckbox in self._representation_checkboxes.items():
            if chckbox.isChecked():
                selected_repres.append(repre_name)

        return selected_repres

    def _update_selected_label(self):
        """Updates label with list of number of selected files."""
        selected_repres = self._get_selected_repres()
        self.files_selected, self.size_selected = \
            self._get_counts(selected_repres)
        self.selected_label.setText(self._prepare_label())

    def _update_template_value(self, _index=None):
        """Sets template value to label after selection in dropdown."""
        name = self.dropdown.currentText()
        template_value = self.templates.get(name)
        if template_value:
            self.btn_delivery.setEnabled(True)
            self.template_label.setText(template_value)

    def _update_progress(self, uploaded):
        """Update progress bar after each repre copied."""
        self.currently_uploaded += uploaded

        ratio = self.currently_uploaded / self.files_selected
        self.progress_bar.setValue(ratio * self.progress_bar.maximum())

    def _format_report(self, result, report_items):
        """Format final result and error details as html."""
        txt = "<h2>{}</h2>".format(result["message"])
        for header, data in report_items.items():
            txt += "<h3>{}</h3>".format(header)
            for item in data:
                txt += "{}<br>".format(item)

        return txt
