from Qt import QtWidgets, QtCore

from .border_label_widget import BorderedLabelWidget

from .card_view_widgets import InstanceCardView
from .list_view_widgets import InstanceListView
from .widgets import (
    SubsetAttributesWidget,
    CreateInstanceBtn,
    RemoveInstanceBtn,
    ChangeViewBtn
)


class CreateOverviewWidget(QtWidgets.QFrame):
    active_changed = QtCore.Signal()
    instance_context_changed = QtCore.Signal()
    create_requested = QtCore.Signal()

    def __init__(self, controller, parent):
        super(CreateOverviewWidget, self).__init__(parent)

        self._controller = controller
        self._refreshing_instances = False

        subset_views_widget = BorderedLabelWidget(
            "Subsets to publish", self
        )

        subset_view_cards = InstanceCardView(controller, subset_views_widget)
        subset_list_view = InstanceListView(controller, subset_views_widget)

        subset_views_layout = QtWidgets.QStackedLayout()
        subset_views_layout.addWidget(subset_view_cards)
        subset_views_layout.addWidget(subset_list_view)

        # Buttons at the bottom of subset view
        create_btn = CreateInstanceBtn(self)
        delete_btn = RemoveInstanceBtn(self)
        change_view_btn = ChangeViewBtn(self)

        # Subset details widget
        subset_attributes_wrap = BorderedLabelWidget(
            "Publish options", self
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
        subset_content_widget = QtWidgets.QWidget(self)
        subset_content_layout = QtWidgets.QHBoxLayout(subset_content_widget)
        subset_content_layout.setContentsMargins(0, 0, 0, 0)
        subset_content_layout.addWidget(subset_views_widget, 3)
        subset_content_layout.addWidget(subset_attributes_wrap, 7)

        # Subset frame layout
        main_layout = QtWidgets.QVBoxLayout(self)
        marings = main_layout.contentsMargins()
        marings.setLeft(marings.left() * 2)
        marings.setRight(marings.right() * 2)
        marings.setTop(marings.top() * 2)
        marings.setBottom(0)
        main_layout.setContentsMargins(marings)
        main_layout.addWidget(subset_content_widget, 1)

        create_btn.clicked.connect(self._on_create_clicked)
        delete_btn.clicked.connect(self._on_delete_clicked)
        change_view_btn.clicked.connect(self._on_change_view_clicked)

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

        controller.add_publish_reset_callback(self._on_publish_reset)
        controller.add_instances_refresh_callback(self._on_instances_refresh)

        self.subset_content_widget = subset_content_widget

        self.subset_view_cards = subset_view_cards
        self.subset_list_view = subset_list_view
        self.subset_views_layout = subset_views_layout

        self.delete_btn = delete_btn

        self.subset_attributes_widget = subset_attributes_widget

    def _on_create_clicked(self):
        """Pass signal to parent widget which should care about changing state.

        We don't change anything here until the parent will care about it.
        """

        self.create_requested.emit()

    def _on_delete_clicked(self):
        instances, _ = self.get_selected_items()

        # Ask user if he really wants to remove instances
        dialog = QtWidgets.QMessageBox(self)
        dialog.setIcon(QtWidgets.QMessageBox.Question)
        dialog.setWindowTitle("Are you sure?")
        if len(instances) > 1:
            msg = (
                "Do you really want to remove {} instances?"
            ).format(len(instances))
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
            self._controller.remove_instances(instances)

    def _on_change_view_clicked(self):
        self._change_view_type()

    def _on_subset_change(self, *_args):
        # Ignore changes if in middle of refreshing
        if self._refreshing_instances:
            return

        instances, context_selected = self.get_selected_items()

        # Disable delete button if nothing is selected
        self.delete_btn.setEnabled(len(instances) > 0)

        self.subset_attributes_widget.set_current_instances(
            instances, context_selected
        )

    def _on_active_changed(self):
        if self._refreshing_instances:
            return
        self.active_changed.emit()

    def _on_instance_context_change(self):
        current_idx = self.subset_views_layout.currentIndex()
        for idx in range(self.subset_views_layout.count()):
            if idx == current_idx:
                continue
            widget = self.subset_views_layout.widget(idx)
            if widget.refreshed:
                widget.set_refreshed(False)

        current_widget = self.subset_views_layout.widget(current_idx)
        current_widget.refresh_instance_states()

        self.instance_context_changed.emit()

    def get_selected_items(self):
        view = self.subset_views_layout.currentWidget()
        return view.get_selected_items()

    def _change_view_type(self):
        idx = self.subset_views_layout.currentIndex()
        new_idx = (idx + 1) % self.subset_views_layout.count()
        self.subset_views_layout.setCurrentIndex(new_idx)

        new_view = self.subset_views_layout.currentWidget()
        if not new_view.refreshed:
            new_view.refresh()
            new_view.set_refreshed(True)
        else:
            new_view.refresh_instance_states()

        self._on_subset_change()

    def _refresh_instances(self):
        if self._refreshing_instances:
            return

        self._refreshing_instances = True

        for idx in range(self.subset_views_layout.count()):
            widget = self.subset_views_layout.widget(idx)
            widget.set_refreshed(False)

        view = self.subset_views_layout.currentWidget()
        view.refresh()
        view.set_refreshed(True)

        self._refreshing_instances = False

        # Force to change instance and refresh details
        self._on_subset_change()

    def _on_publish_reset(self):
        """Context in controller has been refreshed."""

        self.subset_content_widget.setEnabled(self._controller.host_is_valid)

    def _on_instances_refresh(self):
        """Controller refreshed instances."""

        self._refresh_instances()

        # Give a change to process Resize Request
        QtWidgets.QApplication.processEvents()
        # Trigger update geometry of
        widget = self.subset_views_layout.currentWidget()
        widget.updateGeometry()
