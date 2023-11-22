from qtpy import QtWidgets, QtCore

from openpype import AYON_SERVER_ENABLED

from .border_label_widget import BorderedLabelWidget

from .card_view_widgets import InstanceCardView
from .list_view_widgets import InstanceListView
from .widgets import (
    SubsetAttributesWidget,
    CreateInstanceBtn,
    RemoveInstanceBtn,
    ChangeViewBtn,
)
from .create_widget import CreateWidget


class OverviewWidget(QtWidgets.QFrame):
    active_changed = QtCore.Signal()
    instance_context_changed = QtCore.Signal()
    create_requested = QtCore.Signal()
    convert_requested = QtCore.Signal()

    anim_end_value = 200
    anim_duration = 200

    def __init__(self, controller, parent):
        super(OverviewWidget, self).__init__(parent)

        self._refreshing_instances = False
        self._controller = controller

        subset_content_widget = QtWidgets.QWidget(self)

        create_widget = CreateWidget(controller, subset_content_widget)

        # --- Created Subsets/Instances ---
        # Common widget for creation and overview
        subset_views_widget = BorderedLabelWidget(
            "{} to publish".format(
                "Products" if AYON_SERVER_ENABLED else "Subsets"
            ),
            subset_content_widget
        )

        subset_view_cards = InstanceCardView(controller, subset_views_widget)
        subset_list_view = InstanceListView(controller, subset_views_widget)

        subset_views_layout = QtWidgets.QStackedLayout()
        subset_views_layout.addWidget(subset_view_cards)
        subset_views_layout.addWidget(subset_list_view)
        subset_views_layout.setCurrentWidget(subset_view_cards)

        # Buttons at the bottom of subset view
        create_btn = CreateInstanceBtn(subset_views_widget)
        delete_btn = RemoveInstanceBtn(subset_views_widget)
        change_view_btn = ChangeViewBtn(subset_views_widget)

        # --- Overview ---
        # Subset details widget
        subset_attributes_wrap = BorderedLabelWidget(
            "Publish options", subset_content_widget
        )
        subset_attributes_widget = SubsetAttributesWidget(
            controller, subset_attributes_wrap
        )
        subset_attributes_wrap.set_center_widget(subset_attributes_widget)

        # Layout of buttons at the bottom of subset view
        subset_view_btns_layout = QtWidgets.QHBoxLayout()
        subset_view_btns_layout.setContentsMargins(0, 5, 0, 0)
        subset_view_btns_layout.addWidget(create_btn)
        subset_view_btns_layout.addSpacing(5)
        subset_view_btns_layout.addWidget(delete_btn)
        subset_view_btns_layout.addStretch(1)
        subset_view_btns_layout.addWidget(change_view_btn)

        # Layout of view and buttons
        # - widget 'subset_view_widget' is necessary
        # - only layout won't be resized automatically to minimum size hint
        #   on child resize request!
        subset_view_widget = QtWidgets.QWidget(subset_views_widget)
        subset_view_layout = QtWidgets.QVBoxLayout(subset_view_widget)
        subset_view_layout.setContentsMargins(0, 0, 0, 0)
        subset_view_layout.addLayout(subset_views_layout, 1)
        subset_view_layout.addLayout(subset_view_btns_layout, 0)

        subset_views_widget.set_center_widget(subset_view_widget)

        # Whole subset layout with attributes and details
        subset_content_layout = QtWidgets.QHBoxLayout(subset_content_widget)
        subset_content_layout.setContentsMargins(0, 0, 0, 0)
        subset_content_layout.addWidget(create_widget, 7)
        subset_content_layout.addWidget(subset_views_widget, 3)
        subset_content_layout.addWidget(subset_attributes_wrap, 7)

        # Subset frame layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(subset_content_widget, 1)

        change_anim = QtCore.QVariantAnimation()
        change_anim.setStartValue(float(0))
        change_anim.setEndValue(float(self.anim_end_value))
        change_anim.setDuration(self.anim_duration)
        change_anim.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

        # --- Calbacks for instances/subsets view ---
        create_btn.clicked.connect(self._on_create_clicked)
        delete_btn.clicked.connect(self._on_delete_clicked)
        change_view_btn.clicked.connect(self._on_change_view_clicked)

        change_anim.valueChanged.connect(self._on_change_anim)
        change_anim.finished.connect(self._on_change_anim_finished)

        # Selection changed
        subset_list_view.selection_changed.connect(
            self._on_subset_change
        )
        subset_view_cards.selection_changed.connect(
            self._on_subset_change
        )
        # Active instances changed
        subset_list_view.active_changed.connect(
            self._on_active_changed
        )
        subset_view_cards.active_changed.connect(
            self._on_active_changed
        )
        # Instance context has changed
        subset_attributes_widget.instance_context_changed.connect(
            self._on_instance_context_change
        )
        subset_attributes_widget.convert_requested.connect(
            self._on_convert_requested
        )

        # --- Controller callbacks ---
        controller.event_system.add_callback(
            "publish.process.started", self._on_publish_start
        )
        controller.event_system.add_callback(
            "controller.reset.started", self._on_controller_reset_start
        )
        controller.event_system.add_callback(
            "publish.reset.finished", self._on_publish_reset
        )
        controller.event_system.add_callback(
            "instances.refresh.finished", self._on_instances_refresh
        )

        self._subset_content_widget = subset_content_widget
        self._subset_content_layout = subset_content_layout

        self._subset_view_cards = subset_view_cards
        self._subset_list_view = subset_list_view
        self._subset_views_layout = subset_views_layout

        self._create_btn = create_btn
        self._delete_btn = delete_btn

        self._subset_attributes_widget = subset_attributes_widget
        self._create_widget = create_widget
        self._subset_views_widget = subset_views_widget
        self._subset_attributes_wrap = subset_attributes_wrap

        self._change_anim = change_anim

        # Start in create mode
        self._current_state = "create"
        subset_attributes_wrap.setVisible(False)

    def make_sure_animation_is_finished(self):
        if self._change_anim.state() == QtCore.QAbstractAnimation.Running:
            self._change_anim.stop()
        self._on_change_anim_finished()

    def set_state(self, new_state, animate):
        if new_state == self._current_state:
            return

        self._current_state = new_state

        if not animate:
            self.make_sure_animation_is_finished()
            return

        if new_state == "create":
            direction = QtCore.QAbstractAnimation.Backward
        else:
            direction = QtCore.QAbstractAnimation.Forward
        self._change_anim.setDirection(direction)

        if (
            self._change_anim.state() != QtCore.QAbstractAnimation.Running
        ):
            self._start_animation()

    def _start_animation(self):
        views_geo = self._subset_views_widget.geometry()
        layout_spacing = self._subset_content_layout.spacing()
        if self._create_widget.isVisible():
            create_geo = self._create_widget.geometry()
            subset_geo = QtCore.QRect(create_geo)
            subset_geo.moveTop(views_geo.top())
            subset_geo.moveLeft(views_geo.right() + layout_spacing)
            self._subset_attributes_wrap.setVisible(True)

        elif self._subset_attributes_wrap.isVisible():
            subset_geo = self._subset_attributes_wrap.geometry()
            create_geo = QtCore.QRect(subset_geo)
            create_geo.moveTop(views_geo.top())
            create_geo.moveRight(views_geo.left() - (layout_spacing + 1))
            self._create_widget.setVisible(True)
        else:
            self._change_anim.start()
            return

        while self._subset_content_layout.count():
            self._subset_content_layout.takeAt(0)
        self._subset_views_widget.setGeometry(views_geo)
        self._create_widget.setGeometry(create_geo)
        self._subset_attributes_wrap.setGeometry(subset_geo)

        self._change_anim.start()

    def get_subset_views_geo(self):
        parent = self._subset_views_widget.parent()
        global_pos = parent.mapToGlobal(self._subset_views_widget.pos())
        return QtCore.QRect(
            global_pos.x(),
            global_pos.y(),
            self._subset_views_widget.width(),
            self._subset_views_widget.height()
        )

    def has_items(self):
        view = self._subset_views_layout.currentWidget()
        return view.has_items()

    def _on_create_clicked(self):
        """Pass signal to parent widget which should care about changing state.

        We don't change anything here until the parent will care about it.
        """

        self.create_requested.emit()

    def _on_delete_clicked(self):
        instance_ids, _, _ = self.get_selected_items()

        # Ask user if he really wants to remove instances
        dialog = QtWidgets.QMessageBox(self)
        dialog.setIcon(QtWidgets.QMessageBox.Question)
        dialog.setWindowTitle("Are you sure?")
        if len(instance_ids) > 1:
            msg = (
                "Do you really want to remove {} instances?"
            ).format(len(instance_ids))
        else:
            msg = (
                "Do you really want to remove the instance?"
            )
        dialog.setText(msg)
        dialog.setStandardButtons(
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel
        )
        dialog.setDefaultButton(QtWidgets.QMessageBox.Ok)
        dialog.setEscapeButton(QtWidgets.QMessageBox.Cancel)
        dialog.exec_()
        # Skip if OK was not clicked
        if dialog.result() == QtWidgets.QMessageBox.Ok:
            instance_ids = set(instance_ids)
            self._controller.remove_instances(instance_ids)

    def _on_change_view_clicked(self):
        self._change_view_type()

    def _on_subset_change(self, *_args):
        # Ignore changes if in middle of refreshing
        if self._refreshing_instances:
            return

        instance_ids, context_selected, convertor_identifiers = (
            self.get_selected_items()
        )

        # Disable delete button if nothing is selected
        self._delete_btn.setEnabled(len(instance_ids) > 0)

        instances_by_id = self._controller.instances
        instances = [
            instances_by_id[instance_id]
            for instance_id in instance_ids
        ]
        self._subset_attributes_widget.set_current_instances(
            instances, context_selected, convertor_identifiers
        )

    def _on_active_changed(self):
        if self._refreshing_instances:
            return
        self.active_changed.emit()

    def _on_change_anim(self, value):
        self._create_widget.setVisible(True)
        self._subset_attributes_wrap.setVisible(True)
        layout_spacing = self._subset_content_layout.spacing()

        content_width = (
            self._subset_content_widget.width() - (layout_spacing * 2)
        )
        content_height = self._subset_content_widget.height()
        views_width = max(
            int(content_width * 0.3),
            self._subset_views_widget.minimumWidth()
        )
        width = content_width - views_width
        # Visible widths of other widgets
        subset_attrs_width = int((float(width) / self.anim_end_value) * value)
        create_width = width - subset_attrs_width

        views_geo = QtCore.QRect(
            create_width + layout_spacing, 0,
            views_width, content_height
        )
        create_geo = QtCore.QRect(0, 0, width, content_height)
        subset_attrs_geo = QtCore.QRect(create_geo)
        create_geo.moveRight(views_geo.left() - (layout_spacing + 1))
        subset_attrs_geo.moveLeft(views_geo.right() + layout_spacing)

        self._subset_views_widget.setGeometry(views_geo)
        self._create_widget.setGeometry(create_geo)
        self._subset_attributes_wrap.setGeometry(subset_attrs_geo)

    def _on_change_anim_finished(self):
        self._change_visibility_for_state()
        self._subset_content_layout.addWidget(self._create_widget, 7)
        self._subset_content_layout.addWidget(self._subset_views_widget, 3)
        self._subset_content_layout.addWidget(self._subset_attributes_wrap, 7)

    def _change_visibility_for_state(self):
        self._create_widget.setVisible(
            self._current_state == "create"
        )
        self._subset_attributes_wrap.setVisible(
            self._current_state == "publish"
        )

    def _on_instance_context_change(self):
        current_idx = self._subset_views_layout.currentIndex()
        for idx in range(self._subset_views_layout.count()):
            if idx == current_idx:
                continue
            widget = self._subset_views_layout.widget(idx)
            if widget.refreshed:
                widget.set_refreshed(False)

        current_widget = self._subset_views_layout.widget(current_idx)
        current_widget.refresh_instance_states()

        self.instance_context_changed.emit()

    def _on_convert_requested(self):
        self.convert_requested.emit()

    def get_selected_items(self):
        """Selected items in current view widget.

        Returns:
            tuple[list[str], bool, list[str]]: Selected items. List of
                instance ids, context is selected, list of selected legacy
                convertor plugins.
        """

        view = self._subset_views_layout.currentWidget()
        return view.get_selected_items()

    def get_selected_legacy_convertors(self):
        """Selected legacy convertor identifiers.

        Returns:
            list[str]: Selected legacy convertor identifiers.
                Example: ['io.openpype.creators.houdini.legacy']
        """

        _, _, convertor_identifiers = self.get_selected_items()
        return convertor_identifiers

    def _change_view_type(self):
        idx = self._subset_views_layout.currentIndex()
        new_idx = (idx + 1) % self._subset_views_layout.count()

        old_view = self._subset_views_layout.currentWidget()
        new_view = self._subset_views_layout.widget(new_idx)

        if not new_view.refreshed:
            new_view.refresh()
            new_view.set_refreshed(True)
        else:
            new_view.refresh_instance_states()

        instance_ids, context_selected, convertor_identifiers = (
            old_view.get_selected_items()
        )
        new_view.set_selected_items(
            instance_ids, context_selected, convertor_identifiers
        )

        self._subset_views_layout.setCurrentIndex(new_idx)

        self._on_subset_change()

    def _refresh_instances(self):
        if self._refreshing_instances:
            return

        self._refreshing_instances = True

        for idx in range(self._subset_views_layout.count()):
            widget = self._subset_views_layout.widget(idx)
            widget.set_refreshed(False)

        view = self._subset_views_layout.currentWidget()
        view.refresh()
        view.set_refreshed(True)

        self._refreshing_instances = False

        # Force to change instance and refresh details
        self._on_subset_change()

    def _on_publish_start(self):
        """Publish started."""

        self._create_btn.setEnabled(False)
        self._subset_attributes_wrap.setEnabled(False)
        for idx in range(self._subset_views_layout.count()):
            widget = self._subset_views_layout.widget(idx)
            widget.set_active_toggle_enabled(False)

    def _on_controller_reset_start(self):
        """Controller reset started."""

        for idx in range(self._subset_views_layout.count()):
            widget = self._subset_views_layout.widget(idx)
            widget.set_active_toggle_enabled(True)

    def _on_publish_reset(self):
        """Context in controller has been reseted."""

        self._create_btn.setEnabled(True)
        self._subset_attributes_wrap.setEnabled(True)
        self._subset_content_widget.setEnabled(self._controller.host_is_valid)

    def _on_instances_refresh(self):
        """Controller refreshed instances."""

        self._refresh_instances()

        # Give a change to process Resize Request
        QtWidgets.QApplication.processEvents()
        # Trigger update geometry of
        widget = self._subset_views_layout.currentWidget()
        widget.updateGeometry()
