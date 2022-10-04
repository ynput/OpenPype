from Qt import QtWidgets, QtCore, QtGui

from openpype import (
    resources,
    style
)
from openpype.tools.utils import (
    PlaceholderLineEdit,
    MessageOverlayObject,
    PixmapLabel,
)

from .publish_report_viewer import PublishReportViewerWidget
from .control import PublisherController
from .widgets import (
    OverviewWidget,
    ValidationsWidget,
    PublishFrame,

    PublisherTabsWidget,

    StopBtn,
    ResetBtn,
    ValidateBtn,
    PublishBtn,

    HelpButton,
    HelpDialog,
)


class PublisherWindow(QtWidgets.QDialog):
    """Main window of publisher."""
    default_width = 1300
    default_height = 800

    def __init__(self, parent=None, reset_on_show=None):
        super(PublisherWindow, self).__init__(parent)

        self.setWindowTitle("OpenPype publisher")

        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
        self.setWindowIcon(icon)

        if reset_on_show is None:
            reset_on_show = True

        if parent is None:
            on_top_flag = QtCore.Qt.WindowStaysOnTopHint
        else:
            on_top_flag = QtCore.Qt.Dialog

        self.setWindowFlags(
            self.windowFlags()
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowMaximizeButtonHint
            | QtCore.Qt.WindowMinimizeButtonHint
            | QtCore.Qt.WindowCloseButtonHint
            | on_top_flag
        )

        controller = PublisherController()

        help_dialog = HelpDialog(controller, self)

        overlay_object = MessageOverlayObject(self)

        # Header
        header_widget = QtWidgets.QWidget(self)

        icon_pixmap = QtGui.QPixmap(resources.get_openpype_icon_filepath())
        icon_label = PixmapLabel(icon_pixmap, header_widget)
        icon_label.setObjectName("PublishContextLabel")

        context_label = QtWidgets.QLabel(header_widget)
        context_label.setObjectName("PublishContextLabel")

        header_extra_widget = QtWidgets.QWidget(header_widget)

        help_btn = HelpButton(header_widget)

        header_layout = QtWidgets.QHBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 15, 0, 15)
        header_layout.setSpacing(15)
        header_layout.addWidget(icon_label, 0)
        header_layout.addWidget(context_label, 0)
        header_layout.addStretch(1)
        header_layout.addWidget(header_extra_widget, 0)
        header_layout.addWidget(help_btn, 0)

        # Tabs widget under header
        tabs_widget = PublisherTabsWidget(self)
        create_tab = tabs_widget.add_tab("Create", "create")
        tabs_widget.add_tab("Publish", "publish")
        tabs_widget.add_tab("Report", "report")
        tabs_widget.add_tab("Details", "details")

        # Widget where is stacked publish overlay and widgets that should be
        #   covered by it
        under_publish_stack = QtWidgets.QWidget(self)
        # Added wrap widget where all widgets under overlay are added
        # - this is because footer is also under overlay and the top part
        #       is faked with floating frame
        under_publish_widget = QtWidgets.QWidget(under_publish_stack)

        # Footer
        footer_widget = QtWidgets.QWidget(under_publish_widget)
        footer_bottom_widget = QtWidgets.QWidget(footer_widget)

        comment_input = PlaceholderLineEdit(footer_widget)
        comment_input.setObjectName("PublishCommentInput")
        comment_input.setPlaceholderText(
            "Attach a comment to your publish"
        )

        reset_btn = ResetBtn(footer_widget)
        stop_btn = StopBtn(footer_widget)
        validate_btn = ValidateBtn(footer_widget)
        publish_btn = PublishBtn(footer_widget)

        footer_bottom_layout = QtWidgets.QHBoxLayout(footer_bottom_widget)
        footer_bottom_layout.setContentsMargins(0, 0, 0, 0)
        footer_bottom_layout.addStretch(1)
        footer_bottom_layout.addWidget(reset_btn, 0)
        footer_bottom_layout.addWidget(stop_btn, 0)
        footer_bottom_layout.addWidget(validate_btn, 0)
        footer_bottom_layout.addWidget(publish_btn, 0)

        footer_layout = QtWidgets.QVBoxLayout(footer_widget)
        footer_margins = footer_layout.contentsMargins()
        border = 2
        footer_layout.setContentsMargins(
            footer_margins.left() + border,
            footer_margins.top(),
            footer_margins.right() + border,
            footer_margins.bottom() + border
        )
        # Spacer helps keep distance of Publish Frame when comment input
        #   is hidden - so when is shrunken it is not overlaying pages
        footer_spacer = QtWidgets.QWidget(footer_widget)
        footer_spacer.setMinimumHeight(border)
        footer_spacer.setMaximumHeight(border)
        footer_spacer.setVisible(False)

        footer_layout.addWidget(comment_input, 0)
        footer_layout.addWidget(footer_spacer, 0)
        footer_layout.addWidget(footer_bottom_widget, 0)

        # Content
        # - wrap stacked widget under one more widget to be able propagate
        #   margins (QStackedLayout can't have margins)
        content_widget = QtWidgets.QWidget(under_publish_widget)

        content_stacked_widget = QtWidgets.QWidget(content_widget)

        content_layout = QtWidgets.QVBoxLayout(content_widget)
        marings = content_layout.contentsMargins()
        marings.setLeft(marings.left() * 2)
        marings.setRight(marings.right() * 2)
        marings.setTop(marings.top() * 2)
        marings.setBottom(0)
        content_layout.setContentsMargins(marings)
        content_layout.addWidget(content_stacked_widget, 1)

        # Overview - create and attributes part
        overview_widget = OverviewWidget(
            controller, content_stacked_widget
        )

        report_widget = ValidationsWidget(controller, parent)

        # Details - Publish details
        publish_details_widget = PublishReportViewerWidget(
            content_stacked_widget
        )

        content_stacked_layout = QtWidgets.QStackedLayout(
            content_stacked_widget
        )
        content_stacked_layout.setContentsMargins(0, 0, 0, 0)
        content_stacked_layout.setStackingMode(
            QtWidgets.QStackedLayout.StackAll
        )
        content_stacked_layout.addWidget(overview_widget)
        content_stacked_layout.addWidget(report_widget)
        content_stacked_layout.addWidget(publish_details_widget)
        content_stacked_layout.setCurrentWidget(overview_widget)

        under_publish_layout = QtWidgets.QVBoxLayout(under_publish_widget)
        under_publish_layout.setContentsMargins(0, 0, 0, 0)
        under_publish_layout.setSpacing(0)
        under_publish_layout.addWidget(content_widget, 1)
        under_publish_layout.addWidget(footer_widget, 0)

        # Overlay which covers inputs during publishing
        publish_overlay = QtWidgets.QFrame(under_publish_stack)
        publish_overlay.setObjectName("OverlayFrame")

        under_publish_stack_layout = QtWidgets.QStackedLayout(
            under_publish_stack
        )
        under_publish_stack_layout.setContentsMargins(0, 0, 0, 0)
        under_publish_stack_layout.setStackingMode(
            QtWidgets.QStackedLayout.StackAll
        )
        under_publish_stack_layout.addWidget(under_publish_widget)
        under_publish_stack_layout.addWidget(publish_overlay)
        under_publish_stack_layout.setCurrentWidget(under_publish_widget)

        # Add main frame to this window
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(header_widget, 0)
        main_layout.addWidget(tabs_widget, 0)
        main_layout.addWidget(under_publish_stack, 1)

        # Floating publish frame
        publish_frame = PublishFrame(controller, self)

        help_btn.clicked.connect(self._on_help_click)
        tabs_widget.tab_changed.connect(self._on_tab_change)
        overview_widget.active_changed.connect(
            self._on_context_or_active_change
        )
        overview_widget.instance_context_changed.connect(
            self._on_context_or_active_change
        )
        overview_widget.create_requested.connect(
            self._on_create_request
        )

        reset_btn.clicked.connect(self._on_reset_clicked)
        stop_btn.clicked.connect(self._on_stop_clicked)
        validate_btn.clicked.connect(self._on_validate_clicked)
        publish_btn.clicked.connect(self._on_publish_clicked)

        publish_frame.details_page_requested.connect(self._go_to_details_tab)

        controller.event_system.add_callback(
            "instances.refresh.finished", self._on_instances_refresh
        )
        controller.event_system.add_callback(
            "publish.reset.finished", self._on_publish_reset
        )
        controller.event_system.add_callback(
            "publish.process.started", self._on_publish_start
        )
        controller.event_system.add_callback(
            "publish.process.validated", self._on_publish_validated
        )
        controller.event_system.add_callback(
            "publish.process.stopped", self._on_publish_stop
        )
        controller.event_system.add_callback(
            "show.card.message", self._on_overlay_message
        )

        # Store extra header widget for TrayPublisher
        # - can be used to add additional widgets to header between context
        #   label and help button
        self._help_dialog = help_dialog
        self._help_btn = help_btn

        self._header_extra_widget = header_extra_widget

        self._tabs_widget = tabs_widget
        self._create_tab = create_tab

        self._under_publish_stack_layout = under_publish_stack_layout

        self._under_publish_widget = under_publish_widget
        self._publish_overlay = publish_overlay
        self._publish_frame = publish_frame

        self._content_stacked_layout = content_stacked_layout

        self._overview_widget = overview_widget
        self._report_widget = report_widget
        self._publish_details_widget = publish_details_widget

        self._context_label = context_label

        self._comment_input = comment_input
        self._footer_spacer = footer_spacer

        self._stop_btn = stop_btn
        self._reset_btn = reset_btn
        self._validate_btn = validate_btn
        self._publish_btn = publish_btn

        self._overlay_object = overlay_object

        self._controller = controller

        self._first_show = True
        self._reset_on_show = reset_on_show
        self._restart_timer = None
        self._publish_frame_visible = None

        self._set_publish_visibility(False)

    @property
    def controller(self):
        return self._controller

    def showEvent(self, event):
        super(PublisherWindow, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            self._on_first_show()

    def resizeEvent(self, event):
        super(PublisherWindow, self).resizeEvent(event)
        self._update_publish_frame_rect()

    def _on_overlay_message(self, event):
        self._overlay_object.add_message(event["message"])

    def _on_first_show(self):
        self.resize(self.default_width, self.default_height)
        self.setStyleSheet(style.load_stylesheet())
        if not self._reset_on_show:
            return

        # Detach showing - give OS chance to draw the window
        timer = QtCore.QTimer()
        timer.setSingleShot(True)
        timer.setInterval(1)
        timer.timeout.connect(self._on_show_restart_timer)
        self._restart_timer = timer
        timer.start()

    def _on_show_restart_timer(self):
        """Callback for '_restart_timer' timer."""

        self._restart_timer = None
        self.reset()

    def closeEvent(self, event):
        self._controller.save_changes()
        super(PublisherWindow, self).closeEvent(event)

    def reset(self):
        self._controller.reset()

    def set_context_label(self, label):
        self._context_label.setText(label)

    def _update_publish_details_widget(self, force=False):
        if not force and self._tabs_widget.current_tab() != "details":
            return

        report_data = self.controller.get_publish_report()
        self._publish_details_widget.set_report_data(report_data)

    def _on_help_click(self):
        if self._help_dialog.isVisible():
            return

        self._help_dialog.show()

        window = self.window()
        desktop = QtWidgets.QApplication.desktop()
        screen_idx = desktop.screenNumber(window)
        screen = desktop.screen(screen_idx)
        screen_rect = screen.geometry()

        window_geo = window.geometry()
        dialog_x = window_geo.x() + window_geo.width()
        dialog_right = (dialog_x + self._help_dialog.width()) - 1
        diff = dialog_right - screen_rect.right()
        if diff > 0:
            dialog_x -= diff

        self._help_dialog.setGeometry(
            dialog_x, window_geo.y(),
            self._help_dialog.width(), self._help_dialog.height()
        )

    def _on_tab_change(self, old_tab, new_tab):
        if old_tab == "details":
            self._publish_details_widget.close_details_popup()

        if new_tab in ("create", "publish"):
            animate = True
            if old_tab not in ("create", "publish"):
                animate = False
                self._content_stacked_layout.setCurrentWidget(
                    self._overview_widget
                )
            self._overview_widget.set_state(new_tab, animate)

        elif new_tab == "details":
            self._content_stacked_layout.setCurrentWidget(
                self._publish_details_widget
            )
            self._update_publish_details_widget()

        elif new_tab == "report":
            self._content_stacked_layout.setCurrentWidget(
                self._report_widget
            )

    def _on_context_or_active_change(self):
        self._validate_create_instances()

    def _on_create_request(self):
        self._go_to_create_tab()

    def _go_to_create_tab(self):
        self._tabs_widget.set_current_tab("create")

    def _go_to_details_tab(self):
        self._tabs_widget.set_current_tab("details")

    def _go_to_report_tab(self):
        self._tabs_widget.set_current_tab("report")

    def _set_publish_overlay_visibility(self, visible):
        if visible:
            widget = self._publish_overlay
        else:
            widget = self._under_publish_widget
        self._under_publish_stack_layout.setCurrentWidget(widget)

    def _set_publish_visibility(self, visible):
        if visible is self._publish_frame_visible:
            return
        self._publish_frame_visible = visible
        self._publish_frame.setVisible(visible)
        self._update_publish_frame_rect()

    def _on_reset_clicked(self):
        self._controller.reset()

    def _on_stop_clicked(self):
        self._controller.stop_publish()

    def _set_publish_comment(self):
        if self._controller.publish_comment_is_set:
            return

        comment = self._comment_input.text()
        self._controller.set_comment(comment)

    def _on_validate_clicked(self):
        self._set_publish_comment()
        self._controller.validate()

    def _on_publish_clicked(self):
        self._set_publish_comment()
        self._controller.publish()

    def _set_footer_enabled(self, enabled):
        self._reset_btn.setEnabled(True)
        if enabled:
            self._stop_btn.setEnabled(False)
            self._validate_btn.setEnabled(True)
            self._publish_btn.setEnabled(True)
        else:
            self._stop_btn.setEnabled(enabled)
            self._validate_btn.setEnabled(enabled)
            self._publish_btn.setEnabled(enabled)

    def _on_publish_reset(self):
        self._create_tab.setEnabled(True)
        self._set_comment_input_visiblity(True)
        self._set_publish_overlay_visibility(False)
        self._set_publish_visibility(False)
        self._set_footer_enabled(False)
        self._update_publish_details_widget()

    def _on_publish_start(self):
        self._create_tab.setEnabled(False)

        self._reset_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._validate_btn.setEnabled(False)
        self._publish_btn.setEnabled(False)

        self._set_comment_input_visiblity(False)
        self._set_publish_visibility(True)
        self._set_publish_overlay_visibility(True)

        self._publish_details_widget.close_details_popup()

        if self._tabs_widget.is_current_tab(self._create_tab):
            self._tabs_widget.set_current_tab("publish")

    def _on_publish_validated(self):
        self._validate_btn.setEnabled(False)

    def _on_publish_stop(self):
        self._set_publish_overlay_visibility(False)
        self._reset_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
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
                if self._tabs_widget.is_current_tab("publish"):
                    self._go_to_report_tab()

            else:
                publish_enabled = not self._controller.publish_has_finished

        self._validate_btn.setEnabled(validate_enabled)
        self._publish_btn.setEnabled(publish_enabled)

        self._update_publish_details_widget()

    def _validate_create_instances(self):
        if not self._controller.host_is_valid:
            self._set_footer_enabled(True)
            return

        all_valid = None
        for instance in self._controller.instances:
            if not instance["active"]:
                continue

            if not instance.has_valid_context:
                all_valid = False
                break

            if all_valid is None:
                all_valid = True

        self._set_footer_enabled(bool(all_valid))

    def _on_instances_refresh(self):
        self._validate_create_instances()

        context_title = self.controller.get_context_title()
        self.set_context_label(context_title)
        self._update_publish_details_widget()

    def _set_comment_input_visiblity(self, visible):
        self._comment_input.setVisible(visible)
        self._footer_spacer.setVisible(not visible)

    def _update_publish_frame_rect(self):
        if not self._publish_frame_visible:
            return

        window_size = self.size()
        size_hint = self._publish_frame.minimumSizeHint()

        width = window_size.width()
        height = size_hint.height()

        self._publish_frame.resize(width, height)

        self._publish_frame.move(
            0, window_size.height() - height
        )
