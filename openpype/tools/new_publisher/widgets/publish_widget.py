import json

from Qt import QtWidgets, QtCore

from openpype.pipeline import KnownPublishError

from .icons import get_icon
from .validations_widget import ValidationsWidget
from ..publish_log_viewer import PublishReportViewerWidget


class PublishFrame(QtWidgets.QFrame):
    def __init__(self, controller, parent):
        super(PublishFrame, self).__init__(parent)

        self.setObjectName("PublishFrame")

        info_frame = QtWidgets.QFrame(self)
        info_frame.setObjectName("PublishInfoFrame")

        validation_errors_widget = ValidationsWidget(controller, self)

        content_widget = QtWidgets.QWidget(info_frame)
        content_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        info_layout = QtWidgets.QVBoxLayout(info_frame)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.addWidget(content_widget)

        main_label = QtWidgets.QLabel(content_widget)
        main_label.setObjectName("PublishInfoMainLabel")
        main_label.setAlignment(QtCore.Qt.AlignCenter)

        message_label = QtWidgets.QLabel(content_widget)
        message_label.setAlignment(QtCore.Qt.AlignCenter)

        message_label_bottom = QtWidgets.QLabel(content_widget)
        message_label_bottom.setAlignment(QtCore.Qt.AlignCenter)

        instance_label = QtWidgets.QLabel("<Instance name>", content_widget)
        instance_label.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        plugin_label = QtWidgets.QLabel("<Plugin name>", content_widget)
        plugin_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        instance_plugin_layout = QtWidgets.QHBoxLayout()
        instance_plugin_layout.addWidget(instance_label, 1)
        instance_plugin_layout.addWidget(plugin_label, 1)

        progress_widget = QtWidgets.QProgressBar(content_widget)
        progress_widget.setObjectName("PublishProgressBar")

        copy_log_btn = QtWidgets.QPushButton("Copy log", content_widget)
        copy_log_btn.setVisible(False)

        show_details_btn = QtWidgets.QPushButton(
            "Show details", content_widget
        )
        show_details_btn.setVisible(False)

        reset_btn = QtWidgets.QPushButton(content_widget)
        reset_btn.setIcon(get_icon("refresh"))

        stop_btn = QtWidgets.QPushButton(content_widget)
        stop_btn.setIcon(get_icon("stop"))

        validate_btn = QtWidgets.QPushButton(content_widget)
        validate_btn.setIcon(get_icon("validate"))

        publish_btn = QtWidgets.QPushButton(content_widget)
        publish_btn.setIcon(get_icon("play"))

        footer_layout = QtWidgets.QHBoxLayout()
        footer_layout.addWidget(copy_log_btn, 0)
        footer_layout.addWidget(show_details_btn, 0)
        footer_layout.addWidget(message_label_bottom, 1)
        footer_layout.addWidget(reset_btn, 0)
        footer_layout.addWidget(stop_btn, 0)
        footer_layout.addWidget(validate_btn, 0)
        footer_layout.addWidget(publish_btn, 0)

        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setSpacing(5)
        content_layout.setAlignment(QtCore.Qt.AlignCenter)

        content_layout.addWidget(main_label)
        content_layout.addStretch(1)
        content_layout.addWidget(message_label)
        content_layout.addStretch(1)
        content_layout.addLayout(instance_plugin_layout)
        content_layout.addWidget(progress_widget)
        content_layout.addStretch(1)
        content_layout.addLayout(footer_layout)

        publish_widget = QtWidgets.QWidget(self)
        publish_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        publish_layout = QtWidgets.QVBoxLayout(publish_widget)
        publish_layout.addWidget(validation_errors_widget, 1)
        publish_layout.addWidget(info_frame, 0)

        details_widget = PublishReportViewerWidget(self)

        main_layout = QtWidgets.QStackedLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setStackingMode(main_layout.StackOne)
        main_layout.addWidget(publish_widget)
        main_layout.addWidget(details_widget)

        main_layout.setCurrentWidget(publish_widget)

        copy_log_btn.clicked.connect(self._on_copy_log)
        show_details_btn.clicked.connect(self._on_show_details)

        reset_btn.clicked.connect(self._on_reset_clicked)
        stop_btn.clicked.connect(self._on_stop_clicked)
        validate_btn.clicked.connect(self._on_validate_clicked)
        publish_btn.clicked.connect(self._on_publish_clicked)

        controller.add_publish_reset_callback(self._on_publish_reset)
        controller.add_publish_started_callback(self._on_publish_start)
        controller.add_publish_validated_callback(self._on_publish_validated)
        controller.add_publish_stopped_callback(self._on_publish_stop)

        controller.add_instance_change_callback(self._on_instance_change)
        controller.add_plugin_change_callback(self._on_plugin_change)

        self.controller = controller

        self.validation_errors_widget = validation_errors_widget

        self._main_layout = main_layout

        self.info_frame = info_frame
        self.main_label = main_label
        self.message_label = message_label

        self.instance_label = instance_label
        self.plugin_label = plugin_label
        self.progress_widget = progress_widget

        self.copy_log_btn = copy_log_btn
        self.show_details_btn = show_details_btn
        self.message_label_bottom = message_label_bottom
        self.reset_btn = reset_btn
        self.stop_btn = stop_btn
        self.validate_btn = validate_btn
        self.publish_btn = publish_btn

        self.details_widget = details_widget

    def _on_publish_reset(self):
        self._set_success_property()
        self._change_bg_property()
        self._set_progress_visibility(True)

        self.main_label.setText("Hit publish (play button)! If you want")
        self.message_label.setText("")
        self.message_label_bottom.setText("")
        self.copy_log_btn.setVisible(False)
        self.show_details_btn.setVisible(False)

        self.reset_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.validate_btn.setEnabled(True)
        self.publish_btn.setEnabled(True)

        self.progress_widget.setValue(self.controller.publish_progress)
        self.progress_widget.setMaximum(self.controller.publish_max_progress)

    def _on_publish_start(self):
        self.validation_errors_widget.clear()

        self._set_success_property(-1)
        self._change_bg_property()
        self._set_progress_visibility(True)
        self.main_label.setText("Publishing...")
        self.copy_log_btn.setVisible(False)
        self.show_details_btn.setVisible(False)

        self.reset_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.validate_btn.setEnabled(False)
        self.publish_btn.setEnabled(False)

    def _on_publish_validated(self):
        self.validate_btn.setEnabled(False)

    def _on_instance_change(self, context, instance):
        """Change instance label when instance is going to be processed."""
        if instance is None:
            new_name = (
                context.data.get("label")
                or getattr(context, "label", None)
                or context.data.get("name")
                or "Context"
            )
        else:
            new_name = (
                instance.data.get("label")
                or getattr(instance, "label", None)
                or instance.data["name"]
            )

        self.instance_label.setText(new_name)
        QtWidgets.QApplication.processEvents()

    def _on_plugin_change(self, plugin):
        """Change plugin label when instance is going to be processed."""
        plugin_name = plugin.__name__
        if hasattr(plugin, "label") and plugin.label:
            plugin_name = plugin.label

        self.progress_widget.setValue(self.controller.publish_progress)
        self.plugin_label.setText(plugin_name)
        QtWidgets.QApplication.processEvents()

    def _on_publish_stop(self):
        self.progress_widget.setValue(self.controller.publish_progress)
        self.copy_log_btn.setVisible(True)
        self.show_details_btn.setVisible(True)

        self.reset_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        validate_enabled = not self.controller.publish_has_crashed
        publish_enabled = not self.controller.publish_has_crashed
        if validate_enabled:
            validate_enabled = not self.controller.publish_has_validated
        if publish_enabled:
            if (
                self.controller.publish_has_validated
                and self.controller.publish_has_validation_errors
            ):
                publish_enabled = False

            else:
                publish_enabled = not self.controller.publish_has_finished

        self.validate_btn.setEnabled(validate_enabled)
        self.publish_btn.setEnabled(publish_enabled)

        error = self.controller.get_publish_crash_error()
        validation_errors = self.controller.get_validation_errors()
        if error:
            self._set_error(error)

        elif validation_errors:
            self._set_progress_visibility(False)
            self._change_bg_property(1)
            self._set_validation_errors(validation_errors)

        elif self.controller.publish_has_finished:
            self._set_finished()

        else:
            self._set_stopped()

    def _set_stopped(self):
        main_label = "Publish paused"
        if self.controller.publish_has_validated:
            main_label += " - Validation passed"

        self.main_label.setText(main_label)
        self.message_label.setText(
            "Hit publish (play button) to continue."
        )

        self._set_success_property(-1)

    def _set_error(self, error):
        self.main_label.setText("Error happened")
        if isinstance(error, KnownPublishError):
            msg = str(error)
        else:
            msg = (
                "Something went wrong. Send report"
                " to your supervisor or OpenPype."
            )
        self.message_label.setText(msg)
        self.message_label_bottom.setText("")
        self._set_success_property(0)

    def _set_validation_errors(self, validation_errors):
        self.main_label.setText("Your publish didn't pass studio validations")
        self.message_label.setText("")
        self.message_label_bottom.setText("Check results above please")
        self._set_success_property(2)

        self.validation_errors_widget.set_errors(validation_errors)

    def _set_finished(self):
        self.main_label.setText("Finished")
        self.message_label.setText("")
        self.message_label_bottom.setText("")
        self._set_success_property(1)

    def _change_bg_property(self, state=None):
        self.setProperty("state", str(state or ""))
        self.style().polish(self)

    def _set_progress_visibility(self, visible):
        self.instance_label.setVisible(visible)
        self.plugin_label.setVisible(visible)
        self.progress_widget.setVisible(visible)
        self.message_label.setVisible(visible)

    def _set_success_property(self, state=None):
        if state is None:
            state = ""
        else:
            state = str(state)

        for widget in (self.progress_widget, self.info_frame):
            if widget.property("state") != state:
                widget.setProperty("state", state)
                widget.style().polish(widget)

    def _on_copy_log(self):
        logs = self.controller.get_publish_report()
        logs_string = json.dumps(logs, indent=4)

        mime_data = QtCore.QMimeData()
        mime_data.setText(logs_string)
        QtWidgets.QApplication.instance().clipboard().setMimeData(
            mime_data
        )

    def _on_show_details(self):
        self._change_bg_property(2)
        self._main_layout.setCurrentWidget(self.details_widget)
        logs = self.controller.get_publish_report()
        self.details_widget.set_report(logs)

    def _on_reset_clicked(self):
        self.controller.reset()

    def _on_stop_clicked(self):
        self.controller.stop_publish()

    def _on_validate_clicked(self):
        self.controller.validate()

    def _on_publish_clicked(self):
        self.controller.publish()
