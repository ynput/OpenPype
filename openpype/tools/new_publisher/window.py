import os
import sys

openpype_dir = ""
mongo_url = ""
project_name = ""
asset_name = ""
task_name = ""
host_name = ""

os.environ["OPENPYPE_MONGO"] = mongo_url
os.environ["AVALON_MONGO"] = mongo_url
os.environ["AVALON_PROJECT"] = project_name
os.environ["AVALON_ASSET"] = asset_name
os.environ["AVALON_TASK"] = task_name
os.environ["AVALON_APP"] = host_name
os.environ["OPENPYPE_DATABASE_NAME"] = "openpype"
os.environ["AVALON_CONFIG"] = "openpype"
os.environ["AVALON_TIMEOUT"] = "1000"
os.environ["AVALON_DB"] = "avalon"
for path in [
    openpype_dir,
    r"{}\repos\avalon-core".format(openpype_dir),
    r"{}\.venv\Lib\site-packages".format(openpype_dir)
]:
    sys.path.append(path)

from Qt import QtWidgets

from openpype import style
from control import PublisherController
from widgets import (
    PublishOverlayFrame,
    SubsetAttributesWidget,
    InstanceCardView,
    InstanceListView,
    CreateDialog
)


class PublisherWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(PublisherWindow, self).__init__(parent)

        self._first_show = True
        self._refreshing_instances = False

        self._view_type_order = ["card", "list"]
        self._view_type = self._view_type_order[0]
        self._views_refreshed = {}

        controller = PublisherController()

        # TODO Title, Icon, Stylesheet
        main_frame = QtWidgets.QWidget(self)
        # Overlay MUST be created after Main to be painted on top of it
        overlay_frame = PublishOverlayFrame(self)
        overlay_frame.setVisible(False)

        # Header
        header_widget = QtWidgets.QWidget(main_frame)
        context_label = QtWidgets.QLabel(header_widget)
        reset_btn = QtWidgets.QPushButton("Reset", header_widget)

        header_layout = QtWidgets.QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addWidget(context_label, 1)
        header_layout.addWidget(reset_btn, 0)

        # Content
        # Subset widget
        subset_widget = QtWidgets.QWidget(main_frame)

        subset_view_cards = InstanceCardView(controller, subset_widget)
        subset_list_view = InstanceListView(controller, subset_widget)

        subset_view_cards.setVisible(False)
        subset_list_view.setVisible(False)

        # Buttons at the bottom of subset view
        create_btn = QtWidgets.QPushButton("+", subset_widget)
        delete_btn = QtWidgets.QPushButton("-", subset_widget)
        save_btn = QtWidgets.QPushButton("Save", subset_widget)
        change_view_btn = QtWidgets.QPushButton("=", subset_widget)

        # Subset details widget
        subset_attributes_widget = SubsetAttributesWidget(
            controller, subset_widget
        )

        # Layout of buttons at the bottom of subset view
        subset_view_btns_layout = QtWidgets.QHBoxLayout()
        subset_view_btns_layout.setContentsMargins(0, 0, 0, 0)
        subset_view_btns_layout.setSpacing(5)
        subset_view_btns_layout.addWidget(create_btn)
        subset_view_btns_layout.addWidget(delete_btn)
        subset_view_btns_layout.addWidget(save_btn)
        subset_view_btns_layout.addStretch(1)
        subset_view_btns_layout.addWidget(change_view_btn)

        # Layout of view and buttons
        subset_view_layout = QtWidgets.QVBoxLayout()
        subset_view_layout.setContentsMargins(0, 0, 0, 0)
        subset_view_layout.addWidget(subset_view_cards, 1)
        subset_view_layout.addWidget(subset_list_view, 1)
        subset_view_layout.addLayout(subset_view_btns_layout, 0)

        # Whole subset layout with attributes and details
        subset_layout = QtWidgets.QHBoxLayout(subset_widget)
        subset_layout.setContentsMargins(0, 0, 0, 0)
        subset_layout.addLayout(subset_view_layout, 0)
        subset_layout.addWidget(subset_attributes_widget, 1)

        content_layout = QtWidgets.QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(subset_widget)

        # Footer
        message_input = QtWidgets.QLineEdit(main_frame)
        validate_btn = QtWidgets.QPushButton("Validate", main_frame)
        publish_btn = QtWidgets.QPushButton("Publish", main_frame)

        footer_layout = QtWidgets.QHBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addWidget(message_input, 1)
        footer_layout.addWidget(validate_btn, 0)
        footer_layout.addWidget(publish_btn, 0)

        # Main frame
        main_frame_layout = QtWidgets.QVBoxLayout(main_frame)
        main_frame_layout.addWidget(header_widget, 0)
        main_frame_layout.addLayout(content_layout, 1)
        main_frame_layout.addLayout(footer_layout, 0)

        # Add main frame to this window
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.addWidget(main_frame)

        creator_window = CreateDialog(controller, self)

        controller.add_instances_refresh_callback(self._on_instances_refresh)

        reset_btn.clicked.connect(self._on_reset_clicked)

        create_btn.clicked.connect(self._on_create_clicked)
        delete_btn.clicked.connect(self._on_delete_clicked)
        save_btn.clicked.connect(self._on_save_clicked)
        change_view_btn.clicked.connect(self._on_change_view_clicked)

        validate_btn.clicked.connect(self._on_validate_clicked)
        publish_btn.clicked.connect(self._on_publish_clicked)

        subset_list_view.selection_changed.connect(
            self._on_subset_change
        )
        subset_view_cards.selection_changed.connect(
            self._on_subset_change
        )

        controller.add_instance_change_callback(self._on_instance_change)
        controller.add_plugin_change_callback(self._on_plugin_change)
        controller.add_publish_stopped_callback(self._on_publish_stop)

        self.main_frame = main_frame
        self.overlay_frame = overlay_frame

        self.context_label = context_label

        self.subset_view_cards = subset_view_cards
        self.subset_list_view = subset_list_view

        self.delete_btn = delete_btn

        self.subset_attributes_widget = subset_attributes_widget
        self.message_input = message_input
        self.validate_btn = validate_btn
        self.publish_btn = publish_btn

        self.controller = controller

        self.creator_window = creator_window

        self.views_by_type = {
            "card": subset_view_cards,
            "list": subset_list_view
        }

        self._change_view_type(self._view_type)

        self.setStyleSheet(style.load_stylesheet())

        # DEBUGING
        self.set_context_label(
            "<project>/<hierarchy>/<asset>/<task>/<workfile>"
        )

    def resizeEvent(self, event):
        super(PublisherWindow, self).resizeEvent(event)

        self.overlay_frame.resize(self.main_frame.size())

    def moveEvent(self, event):
        super(PublisherWindow, self).moveEvent(event)
        self.overlay_frame.move(self.main_frame.pos())

    def showEvent(self, event):
        super(PublisherWindow, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            self.reset()

    def reset(self):
        self.controller.reset()

    def set_context_label(self, label):
        self.context_label.setText(label)

    def get_selected_instances(self):
        view = self.views_by_type[self._view_type]
        return view.get_selected_instances()

    def _change_view_type(self, view_type=None):
        if view_type is None:
            next_type = False
            for _view_type in self._view_type_order:
                if next_type:
                    view_type = _view_type
                    break

                if _view_type == self._view_type:
                    next_type = True

            if view_type is None:
                view_type = self._view_type_order[0]

        old_view = self.views_by_type[self._view_type]
        old_view.setVisible(False)

        self._view_type = view_type
        refreshed = self._views_refreshed.get(view_type, False)
        new_view = self.views_by_type[view_type]
        new_view.setVisible(True)
        if not refreshed:
            new_view.refresh()
            self._views_refreshed[view_type] = True
        else:
            new_view.refresh_active_state()

        if new_view is not old_view:
            selected_instances = old_view.get_selected_instances()
            new_view.set_selected_instances(selected_instances)

    def _on_reset_clicked(self):
        self.reset()

    def _on_create_clicked(self):
        self.creator_window.show()

    def _on_delete_clicked(self):
        instances = self.get_selected_instances()

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
            self.controller.remove_instances(instances)

    def _on_change_view_clicked(self):
        self._change_view_type()

    def _on_save_clicked(self):
        self.controller.save_instance_changes()

    def _show_overlay(self):
        if self.overlay_frame.isVisible():
            return

        self.overlay_frame.setVisible(True)

    def _on_validate_clicked(self):
        self._show_overlay()
        self.controller.validate()

    def _on_publish_clicked(self):
        self._show_overlay()
        self.controller.publish()

    def _refresh_instances(self):
        if self._refreshing_instances:
            return

        self._refreshing_instances = True

        view = self.views_by_type[self._view_type]
        view.refresh()

        self._views_refreshed = {self._view_type: True}

        self._refreshing_instances = False

        # Force to change instance and refresh details
        self._on_subset_change()

    def _on_instances_refresh(self):
        self._refresh_instances()

    def _on_subset_change(self, *_args):
        # Ignore changes if in middle of refreshing
        if self._refreshing_instances:
            return

        instances = self.get_selected_instances()

        # Disable delete button if nothing is selected
        self.delete_btn.setEnabled(len(instances) >= 0)

        self.subset_attributes_widget.set_current_instances(instances)

    def _on_plugin_change(self, plugin):
        plugin_name = plugin.__name__
        if hasattr(plugin, "label") and plugin.label:
            plugin_name = plugin.label
        self.overlay_frame.set_plugin(plugin_name)

    def _on_instance_change(self, context, instance):
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

        self.overlay_frame.set_instance(new_name)

    def _on_publish_stop(self):
        pass


def main():
    """Main function for testing purposes."""

    app = QtWidgets.QApplication([])
    window = PublisherWindow()
    window.show()
    app.exec_()


if __name__ == "__main__":
    main()
