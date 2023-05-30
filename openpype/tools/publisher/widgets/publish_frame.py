import os
import json
import time

from qtpy import QtWidgets, QtCore

from .widgets import (
    StopBtn,
    ResetBtn,
    ValidateBtn,
    PublishBtn,
    PublishReportBtn,
)


class PublishFrame(QtWidgets.QWidget):
    """Frame showed during publishing.

    Shows all information related to publishing. Contains validation error
    widget which is showed if only validation error happens during validation.

    Processing layer is default layer. Validation error layer is shown if only
    validation exception is raised during publishing. Report layer is available
    only when publishing process is stopped and must be manually triggered to
    change into that layer.

    +------------------------------------------------------------------------+
    |                             < Main label >                             |
    |                             < Label top >                              |
    |        (####                10%  <Progress bar>                )       |
    | <Instance label>                                        <Plugin label> |
    | <Report>                              <Reset><Stop><Validate><Publish> |
    +------------------------------------------------------------------------+
    """

    details_page_requested = QtCore.Signal()

    def __init__(self, controller, borders, parent):
        super(PublishFrame, self).__init__(parent)

        # Bottom part of widget where process and callback buttons are showed
        # - QFrame used to be able set background using stylesheets easily
        #   and not override all children widgets style
        content_frame = QtWidgets.QFrame(self)
        content_frame.setObjectName("PublishInfoFrame")

        top_content_widget = QtWidgets.QWidget(content_frame)

        # Center widget displaying current state (without any specific info)
        main_label = QtWidgets.QLabel(top_content_widget)
        main_label.setObjectName("PublishInfoMainLabel")
        main_label.setAlignment(QtCore.Qt.AlignCenter)

        # Supporting labels for main label
        # Top label is displayed just under main label
        message_label_top = QtWidgets.QLabel(top_content_widget)
        message_label_top.setAlignment(QtCore.Qt.AlignCenter)

        # Label showing currently processed instance
        progress_widget = QtWidgets.QWidget(top_content_widget)
        instance_plugin_widget = QtWidgets.QWidget(progress_widget)
        instance_label = QtWidgets.QLabel(
            "<Instance name>", instance_plugin_widget
        )
        instance_label.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        # Label showing currently processed plugin
        plugin_label = QtWidgets.QLabel(
            "<Plugin name>", instance_plugin_widget
        )
        plugin_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        instance_plugin_layout = QtWidgets.QHBoxLayout(instance_plugin_widget)
        instance_plugin_layout.setContentsMargins(0, 0, 0, 0)
        instance_plugin_layout.addWidget(instance_label, 1)
        instance_plugin_layout.addWidget(plugin_label, 1)

        # Progress bar showing progress of publishing
        progress_bar = QtWidgets.QProgressBar(progress_widget)
        progress_bar.setObjectName("PublishProgressBar")

        progress_layout = QtWidgets.QVBoxLayout(progress_widget)
        progress_layout.setSpacing(5)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.addWidget(instance_plugin_widget, 0)
        progress_layout.addWidget(progress_bar, 0)

        top_content_layout = QtWidgets.QVBoxLayout(top_content_widget)
        top_content_layout.setContentsMargins(0, 0, 0, 0)
        top_content_layout.setSpacing(5)
        top_content_layout.setAlignment(QtCore.Qt.AlignCenter)
        top_content_layout.addWidget(main_label)
        # TODO stretches should be probably replaced by spacing...
        # - stretch in floating frame doesn't make sense
        top_content_layout.addWidget(message_label_top)
        top_content_layout.addWidget(progress_widget)

        # Publishing buttons to stop, reset or trigger publishing
        footer_widget = QtWidgets.QWidget(content_frame)

        report_btn = PublishReportBtn(footer_widget)

        shrunk_main_label = QtWidgets.QLabel(footer_widget)
        shrunk_main_label.setObjectName("PublishInfoMainLabel")
        shrunk_main_label.setAlignment(
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft
        )

        reset_btn = ResetBtn(footer_widget)
        stop_btn = StopBtn(footer_widget)
        validate_btn = ValidateBtn(footer_widget)
        publish_btn = PublishBtn(footer_widget)

        report_btn.add_action("Go to details", "go_to_report")
        report_btn.add_action("Copy report", "copy_report")
        report_btn.add_action("Export report", "export_report")

        # Footer on info frame layout
        footer_layout = QtWidgets.QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addWidget(report_btn, 0)
        footer_layout.addWidget(shrunk_main_label, 1)
        footer_layout.addWidget(reset_btn, 0)
        footer_layout.addWidget(stop_btn, 0)
        footer_layout.addWidget(validate_btn, 0)
        footer_layout.addWidget(publish_btn, 0)

        # Info frame content
        content_layout = QtWidgets.QVBoxLayout(content_frame)
        content_layout.setSpacing(5)

        content_layout.addWidget(top_content_widget)
        content_layout.addWidget(footer_widget)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(borders, 0, borders, borders)
        main_layout.addWidget(content_frame)

        shrunk_anim = QtCore.QVariantAnimation()
        shrunk_anim.setDuration(140)
        shrunk_anim.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

        # Force translucent background for widgets
        for widget in (
            self,
            top_content_widget,
            footer_widget,
            progress_widget,
            instance_plugin_widget,
        ):
            widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        report_btn.triggered.connect(self._on_report_triggered)
        reset_btn.clicked.connect(self._on_reset_clicked)
        stop_btn.clicked.connect(self._on_stop_clicked)
        validate_btn.clicked.connect(self._on_validate_clicked)
        publish_btn.clicked.connect(self._on_publish_clicked)

        shrunk_anim.valueChanged.connect(self._on_shrunk_anim)
        shrunk_anim.finished.connect(self._on_shrunk_anim_finish)

        controller.event_system.add_callback(
            "publish.reset.finished", self._on_publish_reset
        )
        controller.event_system.add_callback(
            "publish.process.started", self._on_publish_start
        )
        controller.event_system.add_callback(
            "publish.has_validated.changed", self._on_publish_validated_change
        )
        controller.event_system.add_callback(
            "publish.process.stopped", self._on_publish_stop
        )

        controller.event_system.add_callback(
            "publish.process.instance.changed", self._on_instance_change
        )
        controller.event_system.add_callback(
            "publish.process.plugin.changed", self._on_plugin_change
        )

        self._shrunk_anim = shrunk_anim

        self._controller = controller

        self._content_frame = content_frame
        self._content_layout = content_layout
        self._top_content_layout = top_content_layout
        self._top_content_widget = top_content_widget

        self._main_label = main_label
        self._message_label_top = message_label_top

        self._instance_label = instance_label
        self._plugin_label = plugin_label

        self._progress_bar = progress_bar
        self._progress_widget = progress_widget

        self._shrunk_main_label = shrunk_main_label
        self._reset_btn = reset_btn
        self._stop_btn = stop_btn
        self._validate_btn = validate_btn
        self._publish_btn = publish_btn

        self._shrunken = False
        self._top_widget_max_height = None
        self._top_widget_size_policy = top_content_widget.sizePolicy()
        self._last_instance_label = None
        self._last_plugin_label = None

    def mouseReleaseEvent(self, event):
        super(PublishFrame, self).mouseReleaseEvent(event)
        self._change_shrunk_state()

    def _change_shrunk_state(self):
        self.set_shrunk_state(not self._shrunken)

    def set_shrunk_state(self, shrunk):
        if shrunk is self._shrunken:
            return

        if self._top_widget_max_height is None:
            self._top_widget_max_height = (
                self._top_content_widget.maximumHeight()
            )

        self._shrunken = shrunk

        anim_is_running = (
            self._shrunk_anim.state() == QtCore.QAbstractAnimation.Running
        )
        if not self.isVisible():
            if anim_is_running:
                self._shrunk_anim.stop()
            self._on_shrunk_anim_finish()
            return

        start = 0
        end = 0
        if shrunk:
            start = self._top_content_widget.height()
        else:
            if anim_is_running:
                start = self._shrunk_anim.currentValue()
            hint = self._top_content_widget.minimumSizeHint()
            end = hint.height()

        self._shrunk_anim.setStartValue(float(start))
        self._shrunk_anim.setEndValue(float(end))
        if not anim_is_running:
            self._shrunk_anim.start()

    def _on_shrunk_anim(self, value):
        diff = self._top_content_widget.height() - int(value)
        if not self._top_content_widget.isVisible():
            diff -= self._content_layout.spacing()

        window_pos = self.pos()
        window_pos_y = window_pos.y() + diff
        window_height = self.height() - diff

        self._top_content_widget.setMinimumHeight(value)
        self._top_content_widget.setMaximumHeight(value)
        self._top_content_widget.setVisible(True)

        self.resize(self.width(), window_height)
        self.move(window_pos.x(), window_pos_y)

    def _on_shrunk_anim_finish(self):
        self._top_content_widget.setVisible(not self._shrunken)
        self._top_content_widget.setMinimumHeight(0)
        self._top_content_widget.setMaximumHeight(
            self._top_widget_max_height
        )
        self._top_content_widget.setSizePolicy(self._top_widget_size_policy)

        if self._shrunken:
            self._shrunk_main_label.setText(self._main_label.text())
        else:
            self._shrunk_main_label.setText("")

        if self._shrunken:
            content_frame_hint = self._content_frame.sizeHint()

            layout = self.layout()
            margins = layout.contentsMargins()
            window_height = (
                content_frame_hint.height()
                + margins.bottom()
                + margins.top()
            )
            diff = self.height() - window_height
            window_pos = self.pos()
            window_pos_y = window_pos.y() + diff
            self.resize(self.width(), window_height)
            self.move(window_pos.x(), window_pos_y)

    def _set_main_label(self, message):
        self._main_label.setText(message)
        if self._shrunken:
            self._shrunk_main_label.setText(message)

    def _on_publish_reset(self):
        self._last_instance_label = None
        self._last_plugin_label = None

        self._set_success_property()
        self._set_progress_visibility(True)

        self._main_label.setText("")
        self._message_label_top.setText("")

        self._reset_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._validate_btn.setEnabled(True)
        self._publish_btn.setEnabled(True)

        self._progress_bar.setValue(self._controller.publish_progress)
        self._progress_bar.setMaximum(self._controller.publish_max_progress)

    def _on_publish_start(self):
        if self._last_plugin_label:
            self._plugin_label.setText(self._last_plugin_label)

        if self._last_instance_label:
            self._instance_label.setText(self._last_instance_label)

        self._set_success_property(3)
        self._set_progress_visibility(True)
        self._set_main_label("Publishing...")
        self._message_label_top.setText("")

        self._reset_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._validate_btn.setEnabled(False)
        self._publish_btn.setEnabled(False)

        self.set_shrunk_state(False)

    def _on_publish_validated_change(self, event):
        if event["value"]:
            self._validate_btn.setEnabled(False)

    def _on_instance_change(self, event):
        """Change instance label when instance is going to be processed."""

        self._last_instance_label = event["instance_label"]
        self._instance_label.setText(event["instance_label"])
        QtWidgets.QApplication.processEvents()

    def _on_plugin_change(self, event):
        """Change plugin label when instance is going to be processed."""

        self._last_plugin_label = event["plugin_label"]
        self._progress_bar.setValue(self._controller.publish_progress)
        self._plugin_label.setText(event["plugin_label"])
        QtWidgets.QApplication.processEvents()

    def _on_publish_stop(self):
        self._progress_bar.setValue(self._controller.publish_progress)

        self._reset_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)

        self._instance_label.setText("")
        self._plugin_label.setText("")

        validate_enabled = not self._controller.publish_has_crashed
        publish_enabled = not self._controller.publish_has_crashed
        if validate_enabled:
            validate_enabled = not self._controller.publish_has_validated
        if publish_enabled:
            if (
                self._controller.publish_has_validated
                and self._controller.publish_has_validation_errors
            ):
                publish_enabled = False

            else:
                publish_enabled = not self._controller.publish_has_finished

        self._validate_btn.setEnabled(validate_enabled)
        self._publish_btn.setEnabled(publish_enabled)

        if self._controller.publish_has_crashed:
            self._set_error_msg()

        elif self._controller.publish_has_validation_errors:
            self._set_progress_visibility(False)
            self._set_validation_errors()

        elif self._controller.publish_has_finished:
            self._set_finished()

        else:
            self._set_stopped()

    def _set_stopped(self):
        main_label = "Publish paused"
        if self._controller.publish_has_validated:
            main_label += " - Validation passed"

        self._set_main_label(main_label)
        self._message_label_top.setText(
            "Hit publish (play button) to continue."
        )

        self._set_success_property(4)

    def _set_error_msg(self):
        """Show error message to artist on publish crash."""

        self._set_main_label("Error happened")

        self._message_label_top.setText(self._controller.publish_error_msg)

        self._set_success_property(1)

    def _set_validation_errors(self):
        self._set_main_label("Your publish didn't pass studio validations")
        self._message_label_top.setText("Check results above please")
        self._set_success_property(2)

    def _set_finished(self):
        self._set_main_label("Finished")
        self._message_label_top.setText("")
        self._set_success_property(0)

    def _set_progress_visibility(self, visible):
        window_height = self.height()
        self._progress_widget.setVisible(visible)
        # Ignore rescaling and move of widget if is shrunken of progress bar
        #   should be visible
        if self._shrunken or visible:
            return

        height = self._progress_widget.height()
        diff = height + self._top_content_layout.spacing()

        window_pos = self.pos()
        window_pos_y = self.pos().y() + diff
        window_height -= diff

        self.resize(self.width(), window_height)
        self.move(window_pos.x(), window_pos_y)

    def _set_success_property(self, state=None):
        """Apply styles by state.

        State enum:
        - None - Default state after restart
        - 0 - Success finish
        - 1 - Error happened
        - 2 - Validation error
        - 3 - In progress
        - 4 - Stopped/Paused
        """

        if state is None:
            state = ""
        else:
            state = str(state)

        for widget in (self._progress_bar, self._content_frame):
            if widget.property("state") != state:
                widget.setProperty("state", state)
                widget.style().polish(widget)

    def _on_report_triggered(self, identifier):
        if identifier == "export_report":
            self._controller.event_system.emit(
                "export_report.request", {}, "publish_frame")

        elif identifier == "copy_report":
            self._controller.event_system.emit(
                "copy_report.request", {}, "publish_frame")

        elif identifier == "go_to_report":
            self.details_page_requested.emit()

    def _on_reset_clicked(self):
        self._controller.reset()

    def _on_stop_clicked(self):
        self._controller.stop_publish()

    def _on_validate_clicked(self):
        self._controller.validate()

    def _on_publish_clicked(self):
        self._controller.publish()
