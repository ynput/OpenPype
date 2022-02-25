import os
import json
import time

from Qt import QtWidgets, QtCore, QtGui

from openpype.pipeline import KnownPublishError

from .validations_widget import ValidationsWidget
from ..publish_report_viewer import PublishReportViewerWidget
from .widgets import (
    StopBtn,
    ResetBtn,
    ValidateBtn,
    PublishBtn,
    CopyPublishReportBtn,
    SavePublishReportBtn,
    ShowPublishReportBtn
)


class ActionsButton(QtWidgets.QToolButton):
    def __init__(self, parent=None):
        super(ActionsButton, self).__init__(parent)

        self.setText("< No action >")
        self.setPopupMode(self.MenuButtonPopup)
        menu = QtWidgets.QMenu(self)

        self.setMenu(menu)

        self._menu = menu
        self._actions = []
        self._current_action = None

        self.clicked.connect(self._on_click)

    def current_action(self):
        return self._current_action

    def add_action(self, action):
        self._actions.append(action)
        action.triggered.connect(self._on_action_trigger)
        self._menu.addAction(action)
        if self._current_action is None:
            self._set_action(action)

    def set_action(self, action):
        if action not in self._actions:
            self.add_action(action)
        self._set_action(action)

    def _set_action(self, action):
        if action is self._current_action:
            return
        self._current_action = action
        self.setText(action.text())
        self.setIcon(action.icon())

    def _on_click(self):
        self._current_action.trigger()

    def _on_action_trigger(self):
        action = self.sender()
        if action not in self._actions:
            return

        self._set_action(action)


class PublishFrame(QtWidgets.QFrame):
    """Frame showed during publishing.

    Shows all information related to publishing. Contains validation error
    widget which is showed if only validation error happens during validation.

    Processing layer is default layer. Validation error layer is shown if only
    validation exception is raised during publishing. Report layer is available
    only when publishing process is stopped and must be manually triggered to
    change into that layer.

    +------------------------------------------------------------------------+
    |                                                                        |
    |                                                                        |
    |                                                                        |
    |                       < Validation error widget >                      |
    |                                                                        |
    |                                                                        |
    |                                                                        |
    |                                                                        |
    +------------------------------------------------------------------------+
    |                             < Main label >                             |
    |                             < Label top >                              |
    |        (####                      10%  <Progress bar>                ) |
    | <Instance label>                                        <Plugin label> |
    | Report: <Copy><Save> <Label bottom>   <Reset><Stop><Validate><Publish> |
    +------------------------------------------------------------------------+
    """
    def __init__(self, controller, parent):
        super(PublishFrame, self).__init__(parent)

        self.setObjectName("PublishFrame")

        # Widget showing validation errors. Their details and action callbacks.
        validation_errors_widget = ValidationsWidget(controller, self)

        # Bottom part of widget where process and callback buttons are showed
        # - QFrame used to be able set background using stylesheets easily
        #   and not override all children widgets style
        info_frame = QtWidgets.QFrame(self)
        info_frame.setObjectName("PublishInfoFrame")

        # Content of info frame
        # - separated into QFrame and QWidget (widget has transparent bg)
        content_widget = QtWidgets.QWidget(info_frame)
        content_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        info_layout = QtWidgets.QVBoxLayout(info_frame)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.addWidget(content_widget)

        # Center widget displaying current state (without any specific info)
        main_label = QtWidgets.QLabel(content_widget)
        main_label.setObjectName("PublishInfoMainLabel")
        main_label.setAlignment(QtCore.Qt.AlignCenter)

        # Supporting labels for main label
        # Top label is displayed just under main label
        message_label_top = QtWidgets.QLabel(content_widget)
        message_label_top.setAlignment(QtCore.Qt.AlignCenter)

        # Bottom label is displayed between report and publish buttons
        #   at bottom part of info frame
        message_label_bottom = QtWidgets.QLabel(content_widget)
        message_label_bottom.setAlignment(QtCore.Qt.AlignCenter)

        # Label showing currently processed instance
        instance_label = QtWidgets.QLabel("<Instance name>", content_widget)
        instance_label.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        # Label showing currently processed plugin
        plugin_label = QtWidgets.QLabel("<Plugin name>", content_widget)
        plugin_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        instance_plugin_layout = QtWidgets.QHBoxLayout()
        instance_plugin_layout.addWidget(instance_label, 1)
        instance_plugin_layout.addWidget(plugin_label, 1)

        # Progress bar showing progress of publishing
        progress_widget = QtWidgets.QProgressBar(content_widget)
        progress_widget.setObjectName("PublishProgressBar")

        # Report buttons to be able copy, save or see report
        report_btns_widget = QtWidgets.QWidget(content_widget)
        report_btns_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        # Hidden by default
        report_btns_widget.setVisible(False)

        report_label = QtWidgets.QLabel("Report:", report_btns_widget)
        copy_report_btn = CopyPublishReportBtn(report_btns_widget)
        export_report_btn = SavePublishReportBtn(report_btns_widget)
        show_details_btn = ShowPublishReportBtn(report_btns_widget)

        report_btns_layout = QtWidgets.QHBoxLayout(report_btns_widget)
        report_btns_layout.setContentsMargins(0, 0, 0, 0)
        report_btns_layout.addWidget(report_label, 0)
        report_btns_layout.addWidget(copy_report_btn, 0)
        report_btns_layout.addWidget(export_report_btn, 0)
        report_btns_layout.addWidget(show_details_btn, 0)

        # Publishing buttons to stop, reset or trigger publishing
        reset_btn = ResetBtn(content_widget)
        stop_btn = StopBtn(content_widget)
        validate_btn = ValidateBtn(content_widget)
        publish_btn = PublishBtn(content_widget)

        # Footer on info frame layout
        info_footer_layout = QtWidgets.QHBoxLayout()
        info_footer_layout.addWidget(report_btns_widget, 0)
        info_footer_layout.addWidget(message_label_bottom, 1)
        info_footer_layout.addWidget(reset_btn, 0)
        info_footer_layout.addWidget(stop_btn, 0)
        info_footer_layout.addWidget(validate_btn, 0)
        info_footer_layout.addWidget(publish_btn, 0)

        # Info frame content
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setSpacing(5)
        content_layout.setAlignment(QtCore.Qt.AlignCenter)

        content_layout.addWidget(main_label)
        content_layout.addStretch(1)
        content_layout.addWidget(message_label_top)
        content_layout.addStretch(1)
        content_layout.addLayout(instance_plugin_layout)
        content_layout.addWidget(progress_widget)
        content_layout.addStretch(1)
        content_layout.addLayout(info_footer_layout)

        # Whole widget layout
        publish_widget = QtWidgets.QWidget(self)
        publish_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        publish_layout = QtWidgets.QVBoxLayout(publish_widget)
        publish_layout.addWidget(validation_errors_widget, 1)
        publish_layout.addWidget(info_frame, 0)

        details_widget = QtWidgets.QWidget(self)
        report_view = PublishReportViewerWidget(details_widget)
        close_report_btn = QtWidgets.QPushButton(details_widget)
        close_report_icon = self._get_report_close_icon()
        close_report_btn.setIcon(close_report_icon)

        details_layout = QtWidgets.QVBoxLayout(details_widget)
        details_layout.addWidget(report_view)
        details_layout.addWidget(close_report_btn)

        main_layout = QtWidgets.QStackedLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setStackingMode(main_layout.StackOne)
        main_layout.addWidget(publish_widget)
        main_layout.addWidget(details_widget)

        main_layout.setCurrentWidget(publish_widget)

        show_details_btn.clicked.connect(self._on_show_details)

        copy_report_btn.clicked.connect(self._on_copy_report)
        export_report_btn.clicked.connect(self._on_export_report)

        reset_btn.clicked.connect(self._on_reset_clicked)
        stop_btn.clicked.connect(self._on_stop_clicked)
        validate_btn.clicked.connect(self._on_validate_clicked)
        publish_btn.clicked.connect(self._on_publish_clicked)

        close_report_btn.clicked.connect(self._on_close_report_clicked)

        controller.add_publish_reset_callback(self._on_publish_reset)
        controller.add_publish_started_callback(self._on_publish_start)
        controller.add_publish_validated_callback(self._on_publish_validated)
        controller.add_publish_stopped_callback(self._on_publish_stop)

        controller.add_instance_change_callback(self._on_instance_change)
        controller.add_plugin_change_callback(self._on_plugin_change)

        self.controller = controller

        self._info_frame = info_frame
        self._publish_widget = publish_widget

        self._validation_errors_widget = validation_errors_widget

        self._main_layout = main_layout

        self._main_label = main_label
        self._message_label_top = message_label_top

        self._instance_label = instance_label
        self._plugin_label = plugin_label

        self._progress_widget = progress_widget

        self._report_btns_widget = report_btns_widget
        self._message_label_bottom = message_label_bottom
        self._reset_btn = reset_btn
        self._stop_btn = stop_btn
        self._validate_btn = validate_btn
        self._publish_btn = publish_btn

        self._details_widget = details_widget
        self._report_view = report_view

    def _get_report_close_icon(self):
        size = 100
        pix = QtGui.QPixmap(size, size)
        pix.fill(QtCore.Qt.transparent)

        half_stroke_size = size / 12
        stroke_size = 2 * half_stroke_size
        size_part = size / 5

        p1 = QtCore.QPoint(half_stroke_size, size_part)
        p2 = QtCore.QPoint(size / 2, size_part * 4)
        p3 = QtCore.QPoint(size - half_stroke_size, size_part)
        painter = QtGui.QPainter(pix)
        pen = QtGui.QPen(QtCore.Qt.white)
        pen.setWidth(stroke_size)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.transparent)
        painter.drawLine(p1, p2)
        painter.drawLine(p2, p3)
        painter.end()

        return QtGui.QIcon(pix)

    def _on_publish_reset(self):
        self._set_success_property()
        self._change_bg_property()
        self._set_progress_visibility(True)

        self._main_label.setText("Hit publish (play button)! If you want")
        self._message_label_top.setText("")
        self._message_label_bottom.setText("")
        self._report_btns_widget.setVisible(False)

        self._reset_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._validate_btn.setEnabled(True)
        self._publish_btn.setEnabled(True)

        self._progress_widget.setValue(self.controller.publish_progress)
        self._progress_widget.setMaximum(self.controller.publish_max_progress)

    def _on_publish_start(self):
        self._validation_errors_widget.clear()

        self._set_success_property(-1)
        self._change_bg_property()
        self._set_progress_visibility(True)
        self._main_label.setText("Publishing...")
        self._report_btns_widget.setVisible(False)

        self._reset_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._validate_btn.setEnabled(False)
        self._publish_btn.setEnabled(False)

    def _on_publish_validated(self):
        self._validate_btn.setEnabled(False)

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

        self._instance_label.setText(new_name)
        QtWidgets.QApplication.processEvents()

    def _on_plugin_change(self, plugin):
        """Change plugin label when instance is going to be processed."""
        plugin_name = plugin.__name__
        if hasattr(plugin, "label") and plugin.label:
            plugin_name = plugin.label

        self._progress_widget.setValue(self.controller.publish_progress)
        self._plugin_label.setText(plugin_name)
        QtWidgets.QApplication.processEvents()

    def _on_publish_stop(self):
        self._progress_widget.setValue(self.controller.publish_progress)
        self._report_btns_widget.setVisible(True)

        self._reset_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
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

        self._validate_btn.setEnabled(validate_enabled)
        self._publish_btn.setEnabled(publish_enabled)

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

        self._main_label.setText(main_label)
        self._message_label_top.setText(
            "Hit publish (play button) to continue."
        )

        self._set_success_property(-1)

    def _set_error(self, error):
        self._main_label.setText("Error happened")
        if isinstance(error, KnownPublishError):
            msg = str(error)
        else:
            msg = (
                "Something went wrong. Send report"
                " to your supervisor or OpenPype."
            )
        self._message_label_top.setText(msg)
        self._message_label_bottom.setText("")
        self._set_success_property(0)

    def _set_validation_errors(self, validation_errors):
        self._main_label.setText("Your publish didn't pass studio validations")
        self._message_label_top.setText("")
        self._message_label_bottom.setText("Check results above please")
        self._set_success_property(2)

        self._validation_errors_widget.set_errors(validation_errors)

    def _set_finished(self):
        self._main_label.setText("Finished")
        self._message_label_top.setText("")
        self._message_label_bottom.setText("")
        self._set_success_property(1)

    def _change_bg_property(self, state=None):
        self.setProperty("state", str(state or ""))
        self.style().polish(self)

    def _set_progress_visibility(self, visible):
        self._instance_label.setVisible(visible)
        self._plugin_label.setVisible(visible)
        self._progress_widget.setVisible(visible)
        self._message_label_top.setVisible(visible)

    def _set_success_property(self, state=None):
        if state is None:
            state = ""
        else:
            state = str(state)

        for widget in (self._progress_widget, self._info_frame):
            if widget.property("state") != state:
                widget.setProperty("state", state)
                widget.style().polish(widget)

    def _on_copy_report(self):
        logs = self.controller.get_publish_report()
        logs_string = json.dumps(logs, indent=4)

        mime_data = QtCore.QMimeData()
        mime_data.setText(logs_string)
        QtWidgets.QApplication.instance().clipboard().setMimeData(
            mime_data
        )

    def _on_export_report(self):
        default_filename = "publish-report-{}".format(
            time.strftime("%y%m%d-%H-%M")
        )
        default_filepath = os.path.join(
            os.path.expanduser("~"),
            default_filename
        )
        new_filepath, ext = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save report", default_filepath, ".json"
        )
        if not ext or not new_filepath:
            return

        logs = self.controller.get_publish_report()
        full_path = new_filepath + ext
        dir_path = os.path.dirname(full_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        with open(full_path, "w") as file_stream:
            json.dump(logs, file_stream)

    def _on_show_details(self):
        self._change_bg_property(2)
        self._main_layout.setCurrentWidget(self._details_widget)
        report_data = self.controller.get_publish_report()
        self._report_view.set_report_data(report_data)

    def _on_close_report_clicked(self):
        self._report_view.close_details_popup()
        if self.controller.get_publish_crash_error():
            self._change_bg_property()

        elif self.controller.get_validation_errors():
            self._change_bg_property(1)
        else:
            self._change_bg_property(2)
        self._main_layout.setCurrentWidget(self._publish_widget)

    def _on_reset_clicked(self):
        self.controller.reset()

    def _on_stop_clicked(self):
        self.controller.stop_publish()

    def _on_validate_clicked(self):
        self.controller.validate()

    def _on_publish_clicked(self):
        self.controller.publish()
