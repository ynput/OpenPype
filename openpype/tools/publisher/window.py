from Qt import QtWidgets, QtCore, QtGui

from openpype import (
    resources,
    style
)
from openpype.tools.utils import (
    PlaceholderLineEdit,
    PixmapLabel
)
from .control import PublisherController
from .widgets import (
    CreateOverviewWidget,
    PublishFrame,

    PublisherTabsWidget,

    CreateDialog,

    StopBtn,
    ResetBtn,
    ValidateBtn,
    PublishBtn,
)


class PublisherWindow(QtWidgets.QDialog):
    """Main window of publisher."""
    default_width = 1200
    default_height = 700

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

        self._reset_on_show = reset_on_show
        self._first_show = True

        controller = PublisherController()

        # Header
        header_widget = QtWidgets.QWidget(self)
        icon_pixmap = QtGui.QPixmap(resources.get_openpype_icon_filepath())
        icon_label = PixmapLabel(icon_pixmap, header_widget)
        icon_label.setObjectName("PublishContextLabel")
        context_label = QtWidgets.QLabel(header_widget)
        context_label.setObjectName("PublishContextLabel")

        header_layout = QtWidgets.QHBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 15, 15, 15)
        header_layout.setSpacing(15)
        header_layout.addWidget(icon_label, 0)
        header_layout.addWidget(context_label, 0)
        header_layout.addStretch(1)

        # Tabs widget under header
        tabs_widget = PublisherTabsWidget(self)
        tabs_widget.add_tab("Create", "create")
        tabs_widget.add_tab("Publish", "publish")
        tabs_widget.add_tab("Report", "report")
        tabs_widget.add_tab("Details", "details")

        # Content
        content_stacked_widget = QtWidgets.QWidget(self)

        create_overview_widget = CreateOverviewWidget(
            controller, content_stacked_widget
        )

        # Footer
        footer_widget = QtWidgets.QWidget(self)
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
        footer_layout.addWidget(comment_input, 0)
        footer_layout.addWidget(footer_bottom_widget, 0)

        # Create publish frame
        publish_frame = PublishFrame(controller, content_stacked_widget)

        content_stacked_layout = QtWidgets.QStackedLayout(
            content_stacked_widget
        )
        content_stacked_layout.setContentsMargins(0, 0, 0, 0)
        content_stacked_layout.setStackingMode(
            QtWidgets.QStackedLayout.StackAll
        )
        content_stacked_layout.addWidget(create_overview_widget)
        content_stacked_layout.addWidget(publish_frame)

        # Add main frame to this window
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(header_widget, 0)
        main_layout.addWidget(tabs_widget, 0)
        main_layout.addWidget(content_stacked_widget, 1)
        main_layout.addWidget(footer_widget, 0)

        creator_window = CreateDialog(controller, parent=self)

        tabs_widget.tab_changed.connect(self._on_tab_change)
        create_overview_widget.active_changed.connect(
            self._on_context_or_active_change
        )
        create_overview_widget.instance_context_changed.connect(
            self._on_context_or_active_change
        )
        create_overview_widget.create_requested.connect(
            self._on_create_request
        )

        reset_btn.clicked.connect(self._on_reset_clicked)
        stop_btn.clicked.connect(self._on_stop_clicked)
        validate_btn.clicked.connect(self._on_validate_clicked)
        publish_btn.clicked.connect(self._on_publish_clicked)

        controller.add_instances_refresh_callback(self._on_instances_refresh)
        controller.add_publish_reset_callback(self._on_publish_reset)
        controller.add_publish_started_callback(self._on_publish_start)
        controller.add_publish_validated_callback(self._on_publish_validated)
        controller.add_publish_stopped_callback(self._on_publish_stop)

        # Store header for TrayPublisher
        self._header_layout = header_layout

        self._tabs_widget = tabs_widget

        self._content_stacked_widget = content_stacked_widget
        self.content_stacked_layout = content_stacked_layout
        self._create_overview_widget = create_overview_widget
        self.publish_frame = publish_frame

        self.context_label = context_label

        self.comment_input = comment_input

        self.stop_btn = stop_btn
        self.reset_btn = reset_btn
        self.validate_btn = validate_btn
        self.publish_btn = publish_btn

        self._controller = controller

        self.creator_window = creator_window

    @property
    def controller(self):
        return self._controller

    def showEvent(self, event):
        super(PublisherWindow, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            self.resize(self.default_width, self.default_height)
            self.setStyleSheet(style.load_stylesheet())
            if self._reset_on_show:
                self.reset()

    def closeEvent(self, event):
        self._controller.save_changes()
        super(PublisherWindow, self).closeEvent(event)

    def reset(self):
        self._controller.reset()

    def set_context_label(self, label):
        self.context_label.setText(label)

    def _on_tab_change(self, prev_tab, new_tab):
        print(prev_tab, new_tab)

    def _on_context_or_active_change(self):
        self._validate_create_instances()

    def _on_create_request(self):
        self._go_to_create_tab()

    def _go_to_create_tab(self):
        self._tabs_widget.set_current_tab("create")

    def _set_publish_visibility(self, visible):
        if visible:
            widget = self.publish_frame
            publish_frame_visible = True
        else:
            widget = self._create_overview_widget
            publish_frame_visible = False
        self.content_stacked_layout.setCurrentWidget(widget)
        self._set_publish_frame_visible(publish_frame_visible)

    def _set_publish_frame_visible(self, publish_frame_visible):
        """Publish frame visibility has changed.

        Also used in TrayPublisher to be able handle start/end of publish
        widget overlay.
        """

        # Hide creator dialog if visible
        if publish_frame_visible and self.creator_window.isVisible():
            self.creator_window.close()

    def _on_reset_clicked(self):
        self._controller.reset()

    def _on_stop_clicked(self):
        self._controller.stop_publish()

    def _set_publish_comment(self):
        if self._controller.publish_comment_is_set:
            return

        comment = self.comment_input.text()
        self._controller.set_comment(comment)

    def _on_validate_clicked(self):
        self._set_publish_comment()
        self._set_publish_visibility(True)
        self._controller.validate()

    def _on_publish_clicked(self):
        self._set_publish_comment()
        self._set_publish_visibility(True)
        self._controller.publish()

    def _set_footer_enabled(self, enabled):
        self.comment_input.setEnabled(enabled)
        self.reset_btn.setEnabled(True)
        if enabled:
            self.stop_btn.setEnabled(False)
            self.validate_btn.setEnabled(True)
            self.publish_btn.setEnabled(True)
        else:
            self.stop_btn.setEnabled(enabled)
            self.validate_btn.setEnabled(enabled)
            self.publish_btn.setEnabled(enabled)

    def _on_publish_reset(self):
        self._set_publish_visibility(False)

        self._set_footer_enabled(False)

    def _on_publish_start(self):
        self.reset_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.validate_btn.setEnabled(False)
        self.publish_btn.setEnabled(False)

    def _on_publish_validated(self):
        self.validate_btn.setEnabled(False)

    def _on_publish_stop(self):
        self.reset_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
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

        self.validate_btn.setEnabled(validate_enabled)
        self.publish_btn.setEnabled(publish_enabled)

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
