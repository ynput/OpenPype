from Qt import QtWidgets, QtCore, QtGui

from openpype.widgets.nice_checkbox import NiceCheckbox

# from openpype.tools.utils import DeselectableTreeView
from .constants import (
    ITEM_ID_ROLE,
    ITEM_IS_GROUP_ROLE
)
from .delegates import GroupItemDelegate
from .model import (
    InstancesModel,
    InstanceProxyModel,
    PluginsModel,
    PluginProxyModel
)
from .report_items import PublishReport

FILEPATH_ROLE = QtCore.Qt.UserRole + 1
TRACEBACK_ROLE = QtCore.Qt.UserRole + 2
IS_DETAIL_ITEM_ROLE = QtCore.Qt.UserRole + 3


class PluginLoadReportModel(QtGui.QStandardItemModel):
    def set_report(self, report):
        parent = self.invisibleRootItem()
        parent.removeRows(0, parent.rowCount())

        new_items = []
        new_items_by_filepath = {}
        for filepath in report.crashed_plugin_paths.keys():
            item = QtGui.QStandardItem(filepath)
            new_items.append(item)
            new_items_by_filepath[filepath] = item

        if not new_items:
            return

        parent.appendRows(new_items)
        for filepath, item in new_items_by_filepath.items():
            traceback_txt = report.crashed_plugin_paths[filepath]
            detail_item = QtGui.QStandardItem()
            detail_item.setData(filepath, FILEPATH_ROLE)
            detail_item.setData(traceback_txt, TRACEBACK_ROLE)
            detail_item.setData(True, IS_DETAIL_ITEM_ROLE)
            item.appendRow(detail_item)


class DetailWidget(QtWidgets.QTextEdit):
    def __init__(self, text, *args, **kwargs):
        super(DetailWidget, self).__init__(*args, **kwargs)

        self.setReadOnly(True)
        self.setHtml(text)
        self.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.setWordWrapMode(
            QtGui.QTextOption.WrapAtWordBoundaryOrAnywhere
        )

    def sizeHint(self):
        content_margins = (
            self.contentsMargins().top()
            + self.contentsMargins().bottom()
        )
        size = self.document().documentLayout().documentSize().toSize()
        size.setHeight(size.height() + content_margins)
        return size


class PluginLoadReportWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(PluginLoadReportWidget, self).__init__(parent)

        view = QtWidgets.QTreeView(self)
        view.setEditTriggers(view.NoEditTriggers)
        view.setTextElideMode(QtCore.Qt.ElideLeft)
        view.setHeaderHidden(True)
        view.setAlternatingRowColors(True)
        view.setVerticalScrollMode(view.ScrollPerPixel)

        model = PluginLoadReportModel()
        view.setModel(model)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(view, 1)

        view.expanded.connect(self._on_expand)

        self._view = view
        self._model = model
        self._widgets_by_filepath = {}

    def _on_expand(self, index):
        for row in range(self._model.rowCount(index)):
            child_index = self._model.index(row, index.column(), index)
            self._create_widget(child_index)

    def showEvent(self, event):
        super(PluginLoadReportWidget, self).showEvent(event)
        self._update_widgets_size_hints()

    def resizeEvent(self, event):
        super(PluginLoadReportWidget, self).resizeEvent(event)
        self._update_widgets_size_hints()

    def _update_widgets_size_hints(self):
        for item in self._widgets_by_filepath.values():
            widget, index = item
            if not widget.isVisible():
                continue
            self._model.setData(
                index, widget.sizeHint(), QtCore.Qt.SizeHintRole
            )

    def _create_widget(self, index):
        if not index.data(IS_DETAIL_ITEM_ROLE):
            return

        filepath = index.data(FILEPATH_ROLE)
        if filepath in self._widgets_by_filepath:
            return

        traceback_txt = index.data(TRACEBACK_ROLE)
        detail_text = (
            "<b>Filepath:</b><br/>"
            "{}<br/><br/>"
            "<b>Traceback:</b><br/>"
            "{}"
        ).format(filepath, traceback_txt.replace("\n", "<br/>"))
        widget = DetailWidget(detail_text, self)
        self._view.setIndexWidget(index, widget)
        self._widgets_by_filepath[filepath] = (widget, index)

    def set_report(self, report):
        self._widgets_by_filepath = {}
        self._model.set_report(report)


class DetailsWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(DetailsWidget, self).__init__(parent)

        output_widget = QtWidgets.QPlainTextEdit(self)
        output_widget.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        output_widget.setObjectName("PublishLogConsole")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(output_widget)

        self._output_widget = output_widget
        self._report_item = None
        self._instance_filter = set()
        self._plugin_filter = set()

    def clear(self):
        self._output_widget.setPlainText("")

    def set_report(self, report):
        self._report_item = report
        self._plugin_filter = set()
        self._instance_filter = set()
        self._update_logs()

    def set_plugin_filter(self, plugin_filter):
        self._plugin_filter = plugin_filter
        self._update_logs()

    def set_instance_filter(self, instance_filter):
        self._instance_filter = instance_filter
        self._update_logs()

    def _update_logs(self):
        if not self._report_item:
            self._output_widget.setPlainText("")
            return

        filtered_logs = []
        for log in self._report_item.logs:
            if (
                self._instance_filter
                and log.instance_id not in self._instance_filter
            ):
                continue

            if (
                self._plugin_filter
                and log.plugin_id not in self._plugin_filter
            ):
                continue
            filtered_logs.append(log)

        self._set_logs(filtered_logs)

    def _set_logs(self, logs):
        lines = []
        for log in logs:
            if log["type"] == "record":
                message = "{}: {}".format(log["levelname"], log["msg"])

                lines.append(message)
                exc_info = log["exc_info"]
                if exc_info:
                    lines.append(exc_info)

            elif log["type"] == "error":
                lines.append(log["traceback"])

            else:
                print(log["type"])

        text = "\n".join(lines)
        self._output_widget.setPlainText(text)


class DeselectableTreeView(QtWidgets.QTreeView):
    """A tree view that deselects on clicking on an empty area in the view"""

    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        clear_selection = False
        if not index.isValid():
            modifiers = QtWidgets.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ShiftModifier:
                return
            elif modifiers == QtCore.Qt.ControlModifier:
                return
            clear_selection = True
        else:
            indexes = self.selectedIndexes()
            if len(indexes) == 1 and index in indexes:
                clear_selection = True

        if clear_selection:
            # clear the selection
            self.clearSelection()
            # clear the current index
            self.setCurrentIndex(QtCore.QModelIndex())
            event.accept()
            return

        QtWidgets.QTreeView.mousePressEvent(self, event)


class DetailsPopup(QtWidgets.QDialog):
    closed = QtCore.Signal()

    def __init__(self, parent, center_widget):
        super(DetailsPopup, self).__init__(parent)
        self.setWindowTitle("Report Details")
        layout = QtWidgets.QHBoxLayout(self)

        self._center_widget = center_widget
        self._first_show = True
        self._layout = layout

    def showEvent(self, event):
        layout = self.layout()
        layout.insertWidget(0, self._center_widget)
        super(DetailsPopup, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            self.resize(700, 400)

    def closeEvent(self, event):
        super(DetailsPopup, self).closeEvent(event)
        self.closed.emit()


class PublishReportViewerWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(PublishReportViewerWidget, self).__init__(parent)

        instances_model = InstancesModel()
        instances_proxy = InstanceProxyModel()
        instances_proxy.setSourceModel(instances_model)

        plugins_model = PluginsModel()
        plugins_proxy = PluginProxyModel()
        plugins_proxy.setSourceModel(plugins_model)

        removed_instances_check = NiceCheckbox(parent=self)
        removed_instances_check.setChecked(instances_proxy.ignore_removed)
        removed_instances_label = QtWidgets.QLabel(
            "Hide removed instances", self
        )

        removed_instances_layout = QtWidgets.QHBoxLayout()
        removed_instances_layout.setContentsMargins(0, 0, 0, 0)
        removed_instances_layout.addWidget(removed_instances_check, 0)
        removed_instances_layout.addWidget(removed_instances_label, 1)

        instances_view = DeselectableTreeView(self)
        instances_view.setObjectName("PublishDetailViews")
        instances_view.setModel(instances_proxy)
        instances_view.setIndentation(0)
        instances_view.setHeaderHidden(True)
        instances_view.setEditTriggers(QtWidgets.QTreeView.NoEditTriggers)
        instances_view.setSelectionMode(QtWidgets.QTreeView.ExtendedSelection)
        instances_view.setExpandsOnDoubleClick(False)

        instances_delegate = GroupItemDelegate(instances_view)
        instances_view.setItemDelegate(instances_delegate)

        skipped_plugins_check = NiceCheckbox(parent=self)
        skipped_plugins_check.setChecked(plugins_proxy.ignore_skipped)
        skipped_plugins_label = QtWidgets.QLabel("Hide skipped plugins", self)

        skipped_plugins_layout = QtWidgets.QHBoxLayout()
        skipped_plugins_layout.setContentsMargins(0, 0, 0, 0)
        skipped_plugins_layout.addWidget(skipped_plugins_check, 0)
        skipped_plugins_layout.addWidget(skipped_plugins_label, 1)

        plugins_view = DeselectableTreeView(self)
        plugins_view.setObjectName("PublishDetailViews")
        plugins_view.setModel(plugins_proxy)
        plugins_view.setIndentation(0)
        plugins_view.setHeaderHidden(True)
        plugins_view.setSelectionMode(QtWidgets.QTreeView.ExtendedSelection)
        plugins_view.setEditTriggers(QtWidgets.QTreeView.NoEditTriggers)
        plugins_view.setExpandsOnDoubleClick(False)

        plugins_delegate = GroupItemDelegate(plugins_view)
        plugins_view.setItemDelegate(plugins_delegate)

        details_widget = QtWidgets.QWidget(self)
        details_tab_widget = QtWidgets.QTabWidget(details_widget)
        details_popup_btn = QtWidgets.QPushButton("PopUp", details_widget)

        details_layout = QtWidgets.QVBoxLayout(details_widget)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.addWidget(details_tab_widget, 1)
        details_layout.addWidget(details_popup_btn, 0)

        details_popup = DetailsPopup(self, details_tab_widget)

        logs_text_widget = DetailsWidget(details_tab_widget)
        plugin_load_report_widget = PluginLoadReportWidget(details_tab_widget)

        details_tab_widget.addTab(logs_text_widget, "Logs")
        details_tab_widget.addTab(plugin_load_report_widget, "Crashed plugins")

        middle_widget = QtWidgets.QWidget(self)
        middle_layout = QtWidgets.QGridLayout(middle_widget)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        # Row 1
        middle_layout.addLayout(removed_instances_layout, 0, 0)
        middle_layout.addLayout(skipped_plugins_layout, 0, 1)
        # Row 2
        middle_layout.addWidget(instances_view, 1, 0)
        middle_layout.addWidget(plugins_view, 1, 1)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(middle_widget, 0)
        layout.addWidget(details_widget, 1)

        instances_view.selectionModel().selectionChanged.connect(
            self._on_instance_change
        )
        instances_view.clicked.connect(self._on_instance_view_clicked)
        plugins_view.clicked.connect(self._on_plugin_view_clicked)
        plugins_view.selectionModel().selectionChanged.connect(
            self._on_plugin_change
        )

        skipped_plugins_check.stateChanged.connect(
            self._on_skipped_plugin_check
        )
        removed_instances_check.stateChanged.connect(
            self._on_removed_instances_check
        )
        details_popup_btn.clicked.connect(self._on_details_popup)
        details_popup.closed.connect(self._on_popup_close)

        self._ignore_selection_changes = False
        self._report_item = None
        self._logs_text_widget = logs_text_widget
        self._plugin_load_report_widget = plugin_load_report_widget

        self._removed_instances_check = removed_instances_check
        self._instances_view = instances_view
        self._instances_model = instances_model
        self._instances_proxy = instances_proxy

        self._instances_delegate = instances_delegate
        self._plugins_delegate = plugins_delegate

        self._skipped_plugins_check = skipped_plugins_check
        self._plugins_view = plugins_view
        self._plugins_model = plugins_model
        self._plugins_proxy = plugins_proxy

        self._details_widget = details_widget
        self._details_tab_widget = details_tab_widget
        self._details_popup = details_popup

    def _on_instance_view_clicked(self, index):
        if not index.isValid() or not index.data(ITEM_IS_GROUP_ROLE):
            return

        if self._instances_view.isExpanded(index):
            self._instances_view.collapse(index)
        else:
            self._instances_view.expand(index)

    def _on_plugin_view_clicked(self, index):
        if not index.isValid() or not index.data(ITEM_IS_GROUP_ROLE):
            return

        if self._plugins_view.isExpanded(index):
            self._plugins_view.collapse(index)
        else:
            self._plugins_view.expand(index)

    def set_report_data(self, report_data):
        report = PublishReport(report_data)
        self.set_report(report)

    def set_report(self, report):
        self._ignore_selection_changes = True

        self._report_item = report

        self._instances_model.set_report(report)
        self._plugins_model.set_report(report)
        self._logs_text_widget.set_report(report)
        self._plugin_load_report_widget.set_report(report)

        self._ignore_selection_changes = False

        self._instances_view.expandAll()
        self._plugins_view.expandAll()

    def _on_instance_change(self, *_args):
        if self._ignore_selection_changes:
            return

        instance_ids = set()
        for index in self._instances_view.selectedIndexes():
            if index.isValid():
                instance_ids.add(index.data(ITEM_ID_ROLE))

        self._logs_text_widget.set_instance_filter(instance_ids)

    def _on_plugin_change(self, *_args):
        if self._ignore_selection_changes:
            return

        plugin_ids = set()
        for index in self._plugins_view.selectedIndexes():
            if index.isValid():
                plugin_ids.add(index.data(ITEM_ID_ROLE))

        self._logs_text_widget.set_plugin_filter(plugin_ids)

    def _on_skipped_plugin_check(self):
        self._plugins_proxy.set_ignore_skipped(
            self._skipped_plugins_check.isChecked()
        )

    def _on_removed_instances_check(self):
        self._instances_proxy.set_ignore_removed(
            self._removed_instances_check.isChecked()
        )

    def _on_details_popup(self):
        self._details_widget.setVisible(False)
        self._details_popup.show()

    def _on_popup_close(self):
        self._details_widget.setVisible(True)
        layout = self._details_widget.layout()
        layout.insertWidget(0, self._details_tab_widget)

    def close_details_popup(self):
        if self._details_popup.isVisible():
            self._details_popup.close()
