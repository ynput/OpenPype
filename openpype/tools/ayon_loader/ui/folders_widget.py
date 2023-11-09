import qtpy
from qtpy import QtWidgets, QtCore, QtGui

from openpype.tools.utils import (
    RecursiveSortFilterProxyModel,
    DeselectableTreeView,
)
from openpype.style import get_objected_colors

from openpype.tools.ayon_utils.widgets import (
    FoldersQtModel,
    FOLDERS_MODEL_SENDER_NAME,
)
from openpype.tools.ayon_utils.widgets.folders_widget import FOLDER_ID_ROLE

if qtpy.API == "pyside":
    from PySide.QtGui import QStyleOptionViewItemV4
elif qtpy.API == "pyqt4":
    from PyQt4.QtGui import QStyleOptionViewItemV4

UNDERLINE_COLORS_ROLE = QtCore.Qt.UserRole + 50


class UnderlinesFolderDelegate(QtWidgets.QItemDelegate):
    """Item delegate drawing bars under folder label.

    This is used in loader tool. Multiselection of folders
    may group products by name under colored groups. Selected color groups are
    then propagated back to selected folders as underlines.
    """
    bar_height = 3

    def __init__(self, *args, **kwargs):
        super(UnderlinesFolderDelegate, self).__init__(*args, **kwargs)
        colors = get_objected_colors("loader", "asset-view")
        self._selected_color = colors["selected"].get_qcolor()
        self._hover_color = colors["hover"].get_qcolor()
        self._selected_hover_color = colors["selected-hover"].get_qcolor()

    def sizeHint(self, option, index):
        """Add bar height to size hint."""
        result = super(UnderlinesFolderDelegate, self).sizeHint(option, index)
        height = result.height()
        result.setHeight(height + self.bar_height)

        return result

    def paint(self, painter, option, index):
        """Replicate painting of an item and draw color bars if needed."""
        # Qt4 compat
        if qtpy.API in ("pyside", "pyqt4"):
            option = QStyleOptionViewItemV4(option)

        painter.save()

        item_rect = QtCore.QRect(option.rect)
        item_rect.setHeight(option.rect.height() - self.bar_height)

        subset_colors = index.data(UNDERLINE_COLORS_ROLE) or []

        subset_colors_width = 0
        if subset_colors:
            subset_colors_width = option.rect.width() / len(subset_colors)

        subset_rects = []
        counter = 0
        for subset_c in subset_colors:
            new_color = None
            new_rect = None
            if subset_c:
                new_color = QtGui.QColor(subset_c)

                new_rect = QtCore.QRect(
                    option.rect.left() + (counter * subset_colors_width),
                    option.rect.top() + (
                        option.rect.height() - self.bar_height
                    ),
                    subset_colors_width,
                    self.bar_height
                )
            subset_rects.append((new_color, new_rect))
            counter += 1

        # Background
        if option.state & QtWidgets.QStyle.State_Selected:
            if len(subset_colors) == 0:
                item_rect.setTop(item_rect.top() + (self.bar_height / 2))

            if option.state & QtWidgets.QStyle.State_MouseOver:
                bg_color = self._selected_hover_color
            else:
                bg_color = self._selected_color
        else:
            item_rect.setTop(item_rect.top() + (self.bar_height / 2))
            if option.state & QtWidgets.QStyle.State_MouseOver:
                bg_color = self._hover_color
            else:
                bg_color = QtGui.QColor()
                bg_color.setAlpha(0)

        # When not needed to do a rounded corners (easier and without
        #   painter restore):
        painter.fillRect(
            option.rect,
            QtGui.QBrush(bg_color)
        )

        if option.state & QtWidgets.QStyle.State_Selected:
            for color, subset_rect in subset_rects:
                if not color or not subset_rect:
                    continue
                painter.fillRect(subset_rect, QtGui.QBrush(color))

        # Icon
        icon_index = index.model().index(
            index.row(), index.column(), index.parent()
        )
        # - Default icon_rect if not icon
        icon_rect = QtCore.QRect(
            item_rect.left(),
            item_rect.top(),
            # To make sure it's same size all the time
            option.rect.height() - self.bar_height,
            option.rect.height() - self.bar_height
        )
        icon = index.model().data(icon_index, QtCore.Qt.DecorationRole)

        if icon:
            mode = QtGui.QIcon.Normal
            if not (option.state & QtWidgets.QStyle.State_Enabled):
                mode = QtGui.QIcon.Disabled
            elif option.state & QtWidgets.QStyle.State_Selected:
                mode = QtGui.QIcon.Selected

            if isinstance(icon, QtGui.QPixmap):
                icon = QtGui.QIcon(icon)
                option.decorationSize = icon.size() / icon.devicePixelRatio()

            elif isinstance(icon, QtGui.QColor):
                pixmap = QtGui.QPixmap(option.decorationSize)
                pixmap.fill(icon)
                icon = QtGui.QIcon(pixmap)

            elif isinstance(icon, QtGui.QImage):
                icon = QtGui.QIcon(QtGui.QPixmap.fromImage(icon))
                option.decorationSize = icon.size() / icon.devicePixelRatio()

            elif isinstance(icon, QtGui.QIcon):
                state = QtGui.QIcon.Off
                if option.state & QtWidgets.QStyle.State_Open:
                    state = QtGui.QIcon.On
                actual_size = option.icon.actualSize(
                    option.decorationSize, mode, state
                )
                option.decorationSize = QtCore.QSize(
                    min(option.decorationSize.width(), actual_size.width()),
                    min(option.decorationSize.height(), actual_size.height())
                )

            state = QtGui.QIcon.Off
            if option.state & QtWidgets.QStyle.State_Open:
                state = QtGui.QIcon.On

            icon.paint(
                painter, icon_rect,
                QtCore.Qt.AlignLeft, mode, state
            )

        # Text
        text_rect = QtCore.QRect(
            icon_rect.left() + icon_rect.width() + 2,
            item_rect.top(),
            item_rect.width(),
            item_rect.height()
        )

        painter.drawText(
            text_rect, QtCore.Qt.AlignVCenter,
            index.data(QtCore.Qt.DisplayRole)
        )

        painter.restore()


class LoaderFoldersModel(FoldersQtModel):
    def __init__(self, *args, **kwargs):
        super(LoaderFoldersModel, self).__init__(*args, **kwargs)

        self._colored_items = set()

    def _fill_item_data(self, item, folder_item):
        """

        Args:
            item (QtGui.QStandardItem): Item to fill data.
            folder_item (FolderItem): Folder item.
        """

        super(LoaderFoldersModel, self)._fill_item_data(item, folder_item)

    def set_merged_products_selection(self, items):
        changes = {
            folder_id: None
            for folder_id in self._colored_items
        }

        all_folder_ids = set()
        for item in items:
            folder_ids = item["folder_ids"]
            all_folder_ids.update(folder_ids)

        for folder_id in all_folder_ids:
            changes[folder_id] = []

        for item in items:
            item_color = item["color"]
            item_folder_ids = item["folder_ids"]
            for folder_id in all_folder_ids:
                folder_color = (
                    item_color
                    if folder_id in item_folder_ids
                    else None
                )
                changes[folder_id].append(folder_color)

        for folder_id, color_value in changes.items():
            item = self._items_by_id.get(folder_id)
            if item is not None:
                item.setData(color_value, UNDERLINE_COLORS_ROLE)

        self._colored_items = all_folder_ids


class LoaderFoldersWidget(QtWidgets.QWidget):
    """Folders widget.

    Widget that handles folders view, model and selection.

    Expected selection handling is disabled by default. If enabled, the
    widget will handle the expected in predefined way. Widget is listening
    to event 'expected_selection_changed' with expected event data below,
    the same data must be available when called method
    'get_expected_selection_data' on controller.

    {
        "folder": {
            "current": bool,               # Folder is what should be set now
            "folder_id": Union[str, None], # Folder id that should be selected
        },
        ...
    }

    Selection is confirmed by calling method 'expected_folder_selected' on
    controller.


    Args:
        controller (AbstractWorkfilesFrontend): The control object.
        parent (QtWidgets.QWidget): The parent widget.
    """

    refreshed = QtCore.Signal()

    def __init__(self, controller, parent):
        super(LoaderFoldersWidget, self).__init__(parent)

        folders_view = DeselectableTreeView(self)
        folders_view.setHeaderHidden(True)
        folders_view.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection)

        folders_model = LoaderFoldersModel(controller)
        folders_proxy_model = RecursiveSortFilterProxyModel()
        folders_proxy_model.setSourceModel(folders_model)
        folders_proxy_model.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)

        folders_label_delegate = UnderlinesFolderDelegate(folders_view)

        folders_view.setModel(folders_proxy_model)
        folders_view.setItemDelegate(folders_label_delegate)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(folders_view, 1)

        controller.register_event_callback(
            "selection.project.changed",
            self._on_project_selection_change,
        )
        controller.register_event_callback(
            "folders.refresh.finished",
            self._on_folders_refresh_finished
        )
        controller.register_event_callback(
            "controller.refresh.finished",
            self._on_controller_refresh
        )
        controller.register_event_callback(
            "expected_selection_changed",
            self._on_expected_selection_change
        )

        selection_model = folders_view.selectionModel()
        selection_model.selectionChanged.connect(self._on_selection_change)

        folders_model.refreshed.connect(self._on_model_refresh)

        self._controller = controller
        self._folders_view = folders_view
        self._folders_model = folders_model
        self._folders_proxy_model = folders_proxy_model
        self._folders_label_delegate = folders_label_delegate

        self._expected_selection = None

    def set_name_filter(self, name):
        """Set filter of folder name.

        Args:
            name (str): The string filter.
        """

        self._folders_proxy_model.setFilterFixedString(name)

    def set_merged_products_selection(self, items):
        """

        Args:
            items (list[dict[str, Any]]): List of merged items with folder
                ids.
        """

        self._folders_model.set_merged_products_selection(items)

    def refresh(self):
        self._folders_model.refresh()

    def _on_project_selection_change(self, event):
        project_name = event["project_name"]
        self._set_project_name(project_name)

    def _set_project_name(self, project_name):
        self._folders_model.set_project_name(project_name)

    def _clear(self):
        self._folders_model.clear()

    def _on_folders_refresh_finished(self, event):
        if event["sender"] != FOLDERS_MODEL_SENDER_NAME:
            self._set_project_name(event["project_name"])

    def _on_controller_refresh(self):
        self._update_expected_selection()

    def _on_model_refresh(self):
        if self._expected_selection:
            self._set_expected_selection()
        self._folders_proxy_model.sort(0)
        self.refreshed.emit()

    def _get_selected_item_ids(self):
        selection_model = self._folders_view.selectionModel()
        item_ids = []
        for index in selection_model.selectedIndexes():
            item_id = index.data(FOLDER_ID_ROLE)
            if item_id is not None:
                item_ids.append(item_id)
        return item_ids

    def _on_selection_change(self):
        item_ids = self._get_selected_item_ids()
        self._controller.set_selected_folders(item_ids)

    # Expected selection handling
    def _on_expected_selection_change(self, event):
        self._update_expected_selection(event.data)

    def _update_expected_selection(self, expected_data=None):
        if expected_data is None:
            expected_data = self._controller.get_expected_selection_data()

        folder_data = expected_data.get("folder")
        if not folder_data or not folder_data["current"]:
            return

        folder_id = folder_data["id"]
        self._expected_selection = folder_id
        if not self._folders_model.is_refreshing:
            self._set_expected_selection()

    def _set_expected_selection(self):
        folder_id = self._expected_selection
        selected_ids = self._get_selected_item_ids()
        self._expected_selection = None
        skip_selection = (
            folder_id is None
            or (
                folder_id in selected_ids
                and len(selected_ids) == 1
            )
        )
        if not skip_selection:
            index = self._folders_model.get_index_by_id(folder_id)
            if index.isValid():
                proxy_index = self._folders_proxy_model.mapFromSource(index)
                self._folders_view.setCurrentIndex(proxy_index)
        self._controller.expected_folder_selected(folder_id)
