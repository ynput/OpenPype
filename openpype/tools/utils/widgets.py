import logging
import time

from . import lib

from Qt import QtWidgets, QtCore, QtGui
from avalon.vendor import qtawesome, qargparse

from avalon import style
from openpype.style import get_objected_colors

from .models import AssetModel, RecursiveSortFilterProxyModel
from .views import AssetsView
from .delegates import AssetDelegate

log = logging.getLogger(__name__)


class PlaceholderLineEdit(QtWidgets.QLineEdit):
    """Set placeholder color of QLineEdit in Qt 5.12 and higher."""
    def __init__(self, *args, **kwargs):
        super(PlaceholderLineEdit, self).__init__(*args, **kwargs)
        self._first_show = True

    def showEvent(self, event):
        super(PlaceholderLineEdit, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            filter_palette = self.palette()
            if hasattr(filter_palette, "PlaceholderText"):
                color_obj = get_objected_colors()["font"]
                color = color_obj.get_qcolor()
                color.setAlpha(67)
                filter_palette.setColor(
                    filter_palette.PlaceholderText,
                    color
                )
                self.setPalette(filter_palette)


class AssetWidget(QtWidgets.QWidget):
    """A Widget to display a tree of assets with filter

    To list the assets of the active project:
        >>> # widget = AssetWidget()
        >>> # widget.refresh()
        >>> # widget.show()

    """

    refresh_triggered = QtCore.Signal()   # on model refresh
    refreshed = QtCore.Signal()
    selection_changed = QtCore.Signal()  # on view selection change
    current_changed = QtCore.Signal()    # on view current index change

    def __init__(self, dbcon, multiselection=False, parent=None):
        super(AssetWidget, self).__init__(parent=parent)

        self.dbcon = dbcon

        # Tree View
        model = AssetModel(dbcon=self.dbcon, parent=self)
        proxy = RecursiveSortFilterProxyModel()
        proxy.setSourceModel(model)
        proxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        view = AssetsView(self)
        view.setModel(proxy)
        if multiselection:
            asset_delegate = AssetDelegate()
            view.setSelectionMode(view.ExtendedSelection)
            view.setItemDelegate(asset_delegate)

        icon = qtawesome.icon("fa.arrow-down", color=style.colors.light)
        set_current_asset_btn = QtWidgets.QPushButton(icon, "")
        set_current_asset_btn.setToolTip("Go to Asset from current Session")
        # Hide by default
        set_current_asset_btn.setVisible(False)

        icon = qtawesome.icon("fa.refresh", color=style.colors.light)
        refresh = QtWidgets.QPushButton(icon, "", parent=self)
        refresh.setToolTip("Refresh items")

        filter_input = QtWidgets.QLineEdit(self)
        filter_input.setPlaceholderText("Filter assets..")

        # Header
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.addWidget(filter_input)
        header_layout.addWidget(set_current_asset_btn)
        header_layout.addWidget(refresh)

        # Layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addLayout(header_layout)
        layout.addWidget(view)

        # Signals/Slots
        filter_input.textChanged.connect(proxy.setFilterFixedString)

        selection = view.selectionModel()
        selection.selectionChanged.connect(self.selection_changed)
        selection.currentChanged.connect(self.current_changed)
        refresh.clicked.connect(self.refresh)
        set_current_asset_btn.clicked.connect(self.set_current_session_asset)

        self.set_current_asset_btn = set_current_asset_btn
        self.model = model
        self.proxy = proxy
        self.view = view

        self.model_selection = {}

    def set_current_asset_btn_visibility(self, visible=None):
        """Hide set current asset button.

        Not all tools support using of current context asset.
        """
        if visible is None:
            visible = not self.set_current_asset_btn.isVisible()
        self.set_current_asset_btn.setVisible(visible)

    def _refresh_model(self):
        # Store selection
        self._store_model_selection()
        time_start = time.time()

        self.set_loading_state(
            loading=True,
            empty=True
        )

        def on_refreshed(has_item):
            self.set_loading_state(loading=False, empty=not has_item)
            self._restore_model_selection()
            self.model.refreshed.disconnect()
            self.refreshed.emit()
            print("Duration: %.3fs" % (time.time() - time_start))

        # Connect to signal
        self.model.refreshed.connect(on_refreshed)
        # Trigger signal before refresh is called
        self.refresh_triggered.emit()
        # Refresh model
        self.model.refresh()

    def refresh(self):
        self._refresh_model()

    def get_active_asset(self):
        """Return the asset item of the current selection."""
        current = self.view.currentIndex()
        return current.data(self.model.ItemRole)

    def get_active_asset_document(self):
        """Return the asset document of the current selection."""
        current = self.view.currentIndex()
        return current.data(self.model.DocumentRole)

    def get_active_index(self):
        return self.view.currentIndex()

    def get_selected_assets(self):
        """Return the documents of selected assets."""
        selection = self.view.selectionModel()
        rows = selection.selectedRows()
        assets = [row.data(self.model.DocumentRole) for row in rows]

        # NOTE: skip None object assumed they are silo (backwards comp.)
        return [asset for asset in assets if asset]

    def select_assets(self, assets, expand=True, key="name"):
        """Select assets by item key.

        Args:
            assets (list): List of asset values that can be found under
                specified `key`
            expand (bool): Whether to also expand to the asset in the view
            key (string): Key that specifies where to look for `assets` values

        Returns:
            None

        Default `key` is "name" in that case `assets` should contain single
        asset name or list of asset names. (It is good idea to use "_id" key
        instead of name in that case `assets` must contain `ObjectId` object/s)
        It is expected that each value in `assets` will be found only once.
        If the filters according to the `key` and `assets` correspond to
        the more asset, only the first found will be selected.

        """

        if not isinstance(assets, (tuple, list)):
            assets = [assets]

        # convert to list - tuple cant be modified
        assets = set(assets)

        # Clear selection
        selection_model = self.view.selectionModel()
        selection_model.clearSelection()

        # Select
        mode = selection_model.Select | selection_model.Rows
        for index in lib.iter_model_rows(
            self.proxy, column=0, include_root=False
        ):
            # stop iteration if there are no assets to process
            if not assets:
                break

            value = index.data(self.model.ItemRole).get(key)
            if value not in assets:
                continue

            # Remove processed asset
            assets.discard(value)

            selection_model.select(index, mode)
            if expand:
                # Expand parent index
                self.view.expand(self.proxy.parent(index))

            # Set the currently active index
            self.view.setCurrentIndex(index)

    def set_loading_state(self, loading, empty):
        if self.view.is_loading != loading:
            if loading:
                self.view.spinner.repaintNeeded.connect(
                    self.view.viewport().update
                )
            else:
                self.view.spinner.repaintNeeded.disconnect()

        self.view.is_loading = loading
        self.view.is_empty = empty

    def _store_model_selection(self):
        index = self.view.currentIndex()
        current = None
        if index and index.isValid():
            current = index.data(self.model.ObjectIdRole)

        expanded = set()
        model = self.view.model()
        for index in lib.iter_model_rows(
            model, column=0, include_root=False
        ):
            if self.view.isExpanded(index):
                value = index.data(self.model.ObjectIdRole)
                expanded.add(value)

        selection_model = self.view.selectionModel()

        selected = None
        selected_rows = selection_model.selectedRows()
        if selected_rows:
            selected = set(
                row.data(self.model.ObjectIdRole)
                for row in selected_rows
            )

        self.model_selection = {
            "expanded": expanded,
            "selected": selected,
            "current": current
        }

    def _restore_model_selection(self):
        model = self.view.model()
        not_set = object()
        expanded = self.model_selection.pop("expanded", not_set)
        selected = self.model_selection.pop("selected", not_set)
        current = self.model_selection.pop("current", not_set)

        if (
            expanded is not_set
            or selected is not_set
            or current is not_set
        ):
            return

        if expanded:
            for index in lib.iter_model_rows(
                model, column=0, include_root=False
            ):
                is_expanded = index.data(self.model.ObjectIdRole) in expanded
                self.view.setExpanded(index, is_expanded)

        if not selected and not current:
            self.set_current_session_asset()
            return

        current_index = None
        selected_indexes = []
        # Go through all indices, select the ones with similar data
        for index in lib.iter_model_rows(
            model, column=0, include_root=False
        ):
            object_id = index.data(self.model.ObjectIdRole)
            if object_id in selected:
                selected_indexes.append(index)

            if not current_index and object_id == current:
                current_index = index

        if current_index:
            self.view.setCurrentIndex(current_index)

        if not selected_indexes:
            return
        selection_model = self.view.selectionModel()
        flags = selection_model.Select | selection_model.Rows
        for index in selected_indexes:
            # Ensure item is visible
            self.view.scrollTo(index)
            selection_model.select(index, flags)

    def set_current_session_asset(self):
        asset_name = self.dbcon.Session.get("AVALON_ASSET")
        if asset_name:
            self.select_assets([asset_name])


class OptionalMenu(QtWidgets.QMenu):
    """A subclass of `QtWidgets.QMenu` to work with `OptionalAction`

    This menu has reimplemented `mouseReleaseEvent`, `mouseMoveEvent` and
    `leaveEvent` to provide better action hightlighting and triggering for
    actions that were instances of `QtWidgets.QWidgetAction`.

    """
    def mouseReleaseEvent(self, event):
        """Emit option clicked signal if mouse released on it"""
        active = self.actionAt(event.pos())
        if active and active.use_option:
            option = active.widget.option
            if option.is_hovered(event.globalPos()):
                option.clicked.emit()
        super(OptionalMenu, self).mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        """Add highlight to active action"""
        active = self.actionAt(event.pos())
        for action in self.actions():
            action.set_highlight(action is active, event.globalPos())
        super(OptionalMenu, self).mouseMoveEvent(event)

    def leaveEvent(self, event):
        """Remove highlight from all actions"""
        for action in self.actions():
            action.set_highlight(False)
        super(OptionalMenu, self).leaveEvent(event)


class OptionalAction(QtWidgets.QWidgetAction):
    """Menu action with option box

    A menu action like Maya's menu item with option box, implemented by
    subclassing `QtWidgets.QWidgetAction`.

    """

    def __init__(self, label, icon, use_option, parent):
        super(OptionalAction, self).__init__(parent)
        self.label = label
        self.icon = icon
        self.use_option = use_option
        self.option_tip = ""
        self.optioned = False
        self.widget = None

    def createWidget(self, parent):
        widget = OptionalActionWidget(self.label, parent)
        self.widget = widget

        if self.icon:
            widget.setIcon(self.icon)

        if self.use_option:
            widget.option.clicked.connect(self.on_option)
            widget.option.setToolTip(self.option_tip)
        else:
            widget.option.setVisible(False)

        return widget

    def set_option_tip(self, options):
        sep = "\n\n"
        mak = (lambda opt: opt["name"] + " :\n    " + opt["help"])
        self.option_tip = sep.join(mak(opt) for opt in options)

    def on_option(self):
        self.optioned = True

    def set_highlight(self, state, global_pos=None):
        option_state = False
        if self.use_option:
            option_state = self.widget.option.is_hovered(global_pos)
        self.widget.set_hover_properties(state, option_state)


class OptionalActionWidget(QtWidgets.QWidget):
    """Main widget class for `OptionalAction`"""

    def __init__(self, label, parent=None):
        super(OptionalActionWidget, self).__init__(parent)

        body_widget = QtWidgets.QWidget(self)
        body_widget.setObjectName("OptionalActionBody")

        icon = QtWidgets.QLabel(body_widget)
        label = QtWidgets.QLabel(label, body_widget)
        # (NOTE) For removing ugly QLable shadow FX when highlighted in Nuke.
        #   See https://stackoverflow.com/q/52838690/4145300
        label.setStyle(QtWidgets.QStyleFactory.create("Plastique"))
        option = OptionBox(body_widget)
        option.setObjectName("OptionalActionOption")

        icon.setFixedSize(24, 16)
        option.setFixedSize(30, 30)

        body_layout = QtWidgets.QHBoxLayout(body_widget)
        body_layout.setContentsMargins(4, 0, 4, 0)
        body_layout.setSpacing(2)
        body_layout.addWidget(icon)
        body_layout.addWidget(label)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(2, 1, 2, 1)
        layout.setSpacing(0)
        layout.addWidget(body_widget)
        layout.addWidget(option)

        body_widget.setMouseTracking(True)
        label.setMouseTracking(True)
        option.setMouseTracking(True)
        self.setMouseTracking(True)
        self.setFixedHeight(32)

        self.icon = icon
        self.label = label
        self.option = option
        self.body = body_widget

    def set_hover_properties(self, hovered, option_hovered):
        body_state = ""
        option_state = ""
        if hovered:
            body_state = "hover"

        if option_hovered:
            option_state = "hover"

        if self.body.property("state") != body_state:
            self.body.setProperty("state", body_state)
            self.body.style().polish(self.body)

        if self.option.property("state") != option_state:
            self.option.setProperty("state", option_state)
            self.option.style().polish(self.option)

    def setIcon(self, icon):
        pixmap = icon.pixmap(16, 16)
        self.icon.setPixmap(pixmap)


class OptionBox(QtWidgets.QLabel):
    """Option box widget class for `OptionalActionWidget`"""

    clicked = QtCore.Signal()

    def __init__(self, parent):
        super(OptionBox, self).__init__(parent)

        self.setAlignment(QtCore.Qt.AlignCenter)

        icon = qtawesome.icon("fa.sticky-note-o", color="#c6c6c6")
        pixmap = icon.pixmap(18, 18)
        self.setPixmap(pixmap)

    def is_hovered(self, global_pos):
        if global_pos is None:
            return False
        pos = self.mapFromGlobal(global_pos)
        return self.rect().contains(pos)


class OptionDialog(QtWidgets.QDialog):
    """Option dialog shown by option box"""

    def __init__(self, parent=None):
        super(OptionDialog, self).__init__(parent)
        self.setModal(True)
        self._options = dict()

    def create(self, options):
        parser = qargparse.QArgumentParser(arguments=options)

        decision_widget = QtWidgets.QWidget(self)
        accept_btn = QtWidgets.QPushButton("Accept", decision_widget)
        cancel_btn = QtWidgets.QPushButton("Cancel", decision_widget)

        decision_layout = QtWidgets.QHBoxLayout(decision_widget)
        decision_layout.addWidget(accept_btn)
        decision_layout.addWidget(cancel_btn)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(parser)
        layout.addWidget(decision_widget)

        accept_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        parser.changed.connect(self.on_changed)

    def on_changed(self, argument):
        self._options[argument["name"]] = argument.read()

    def parse(self):
        return self._options.copy()
