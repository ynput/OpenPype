import re

from qtpy import QtWidgets, QtCore, QtGui

from openpype import AYON_SERVER_ENABLED
from openpype.pipeline.create import (
    SUBSET_NAME_ALLOWED_SYMBOLS,
    PRE_CREATE_THUMBNAIL_KEY,
    DEFAULT_VARIANT_VALUE,
    TaskNotSetError,
)

from .thumbnail_widget import ThumbnailWidget
from .widgets import (
    IconValuePixmapLabel,
    CreateBtn,
)
from .assets_widget import CreateWidgetAssetsWidget
from .tasks_widget import CreateWidgetTasksWidget
from .precreate_widget import PreCreateWidget
from ..constants import (
    VARIANT_TOOLTIP,
    FAMILY_ROLE,
    CREATOR_IDENTIFIER_ROLE,
    CREATOR_THUMBNAIL_ENABLED_ROLE,
    CREATOR_SORT_ROLE,
    INPUTS_LAYOUT_HSPACING,
    INPUTS_LAYOUT_VSPACING,
)

SEPARATORS = ("---separator---", "---")


class ResizeControlWidget(QtWidgets.QWidget):
    resized = QtCore.Signal()

    def resizeEvent(self, event):
        super(ResizeControlWidget, self).resizeEvent(event)
        self.resized.emit()


# TODO add creator identifier/label to details
class CreatorShortDescWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(CreatorShortDescWidget, self).__init__(parent=parent)

        # --- Short description widget ---
        icon_widget = IconValuePixmapLabel(None, self)
        icon_widget.setObjectName("FamilyIconLabel")

        # --- Short description inputs ---
        short_desc_input_widget = QtWidgets.QWidget(self)

        family_label = QtWidgets.QLabel(short_desc_input_widget)
        family_label.setAlignment(
            QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeft
        )

        description_label = QtWidgets.QLabel(short_desc_input_widget)
        description_label.setAlignment(
            QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft
        )

        short_desc_input_layout = QtWidgets.QVBoxLayout(
            short_desc_input_widget
        )
        short_desc_input_layout.setSpacing(0)
        short_desc_input_layout.addWidget(family_label)
        short_desc_input_layout.addWidget(description_label)
        # --------------------------------

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(icon_widget, 0)
        layout.addWidget(short_desc_input_widget, 1)
        # --------------------------------

        self._icon_widget = icon_widget
        self._family_label = family_label
        self._description_label = description_label

    def set_creator_item(self, creator_item=None):
        if not creator_item:
            self._icon_widget.set_icon_def(None)
            self._family_label.setText("")
            self._description_label.setText("")
            return

        plugin_icon = creator_item.icon
        description = creator_item.description or ""

        self._icon_widget.set_icon_def(plugin_icon)
        self._family_label.setText("<b>{}</b>".format(creator_item.family))
        self._family_label.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self._description_label.setText(description)


class CreatorsProxyModel(QtCore.QSortFilterProxyModel):
    def lessThan(self, left, right):
        l_show_order = left.data(CREATOR_SORT_ROLE)
        r_show_order = right.data(CREATOR_SORT_ROLE)
        if l_show_order == r_show_order:
            return super(CreatorsProxyModel, self).lessThan(left, right)
        return l_show_order < r_show_order


class CreateWidget(QtWidgets.QWidget):
    def __init__(self, controller, parent=None):
        super(CreateWidget, self).__init__(parent)

        self._controller = controller

        self._asset_name = None
        self._subset_names = None
        self._selected_creator = None

        self._prereq_available = False

        name_pattern = "^[{}]*$".format(SUBSET_NAME_ALLOWED_SYMBOLS)
        self._name_pattern = name_pattern
        self._compiled_name_pattern = re.compile(name_pattern)

        main_splitter_widget = QtWidgets.QSplitter(self)

        context_widget = QtWidgets.QWidget(main_splitter_widget)

        assets_widget = CreateWidgetAssetsWidget(controller, context_widget)
        tasks_widget = CreateWidgetTasksWidget(controller, context_widget)

        context_layout = QtWidgets.QVBoxLayout(context_widget)
        context_layout.setContentsMargins(0, 0, 0, 0)
        context_layout.setSpacing(0)
        context_layout.addWidget(assets_widget, 2)
        context_layout.addWidget(tasks_widget, 1)

        # --- Creators view ---
        creators_widget = QtWidgets.QWidget(main_splitter_widget)

        creator_short_desc_widget = CreatorShortDescWidget(creators_widget)

        attr_separator_widget = QtWidgets.QWidget(creators_widget)
        attr_separator_widget.setObjectName("Separator")
        attr_separator_widget.setMinimumHeight(1)
        attr_separator_widget.setMaximumHeight(1)

        creators_splitter = QtWidgets.QSplitter(creators_widget)

        creators_view_widget = QtWidgets.QWidget(creators_splitter)

        creator_view_label = QtWidgets.QLabel(
            "Choose publish type", creators_view_widget
        )

        creators_view = QtWidgets.QListView(creators_view_widget)
        creators_model = QtGui.QStandardItemModel()
        creators_sort_model = CreatorsProxyModel()
        creators_sort_model.setSourceModel(creators_model)
        creators_view.setModel(creators_sort_model)

        creators_view_layout = QtWidgets.QVBoxLayout(creators_view_widget)
        creators_view_layout.setContentsMargins(0, 0, 0, 0)
        creators_view_layout.addWidget(creator_view_label, 0)
        creators_view_layout.addWidget(creators_view, 1)

        # --- Creator attr defs ---
        creators_attrs_widget = QtWidgets.QWidget(creators_splitter)

        # Top part - variant / subset name + thumbnail
        creators_attrs_top = QtWidgets.QWidget(creators_attrs_widget)

        # Basics - variant / subset name
        creator_basics_widget = ResizeControlWidget(creators_attrs_top)

        variant_subset_label = QtWidgets.QLabel(
            "Create options", creator_basics_widget
        )

        variant_subset_widget = QtWidgets.QWidget(creator_basics_widget)
        # Variant and subset input
        variant_widget = ResizeControlWidget(variant_subset_widget)
        variant_widget.setObjectName("VariantInputsWidget")

        variant_input = QtWidgets.QLineEdit(variant_widget)
        variant_input.setObjectName("VariantInput")
        variant_input.setToolTip(VARIANT_TOOLTIP)

        variant_hints_btn = QtWidgets.QToolButton(variant_widget)
        variant_hints_btn.setArrowType(QtCore.Qt.DownArrow)
        variant_hints_btn.setIconSize(QtCore.QSize(12, 12))

        variant_hints_menu = QtWidgets.QMenu(variant_widget)
        variant_hints_group = QtWidgets.QActionGroup(variant_hints_menu)

        variant_layout = QtWidgets.QHBoxLayout(variant_widget)
        variant_layout.setContentsMargins(0, 0, 0, 0)
        variant_layout.setSpacing(0)
        variant_layout.addWidget(variant_input, 1)
        variant_layout.addWidget(variant_hints_btn, 0, QtCore.Qt.AlignVCenter)

        subset_name_input = QtWidgets.QLineEdit(variant_subset_widget)
        subset_name_input.setEnabled(False)

        variant_subset_layout = QtWidgets.QFormLayout(variant_subset_widget)
        variant_subset_layout.setContentsMargins(0, 0, 0, 0)
        variant_subset_layout.setHorizontalSpacing(INPUTS_LAYOUT_HSPACING)
        variant_subset_layout.setVerticalSpacing(INPUTS_LAYOUT_VSPACING)
        variant_subset_layout.addRow("Variant", variant_widget)
        variant_subset_layout.addRow(
            "Product" if AYON_SERVER_ENABLED else "Subset",
            subset_name_input)

        creator_basics_layout = QtWidgets.QVBoxLayout(creator_basics_widget)
        creator_basics_layout.setContentsMargins(0, 0, 0, 0)
        creator_basics_layout.addWidget(variant_subset_label, 0)
        creator_basics_layout.addWidget(variant_subset_widget, 0)

        thumbnail_widget = ThumbnailWidget(controller, creators_attrs_top)

        creators_attrs_top_layout = QtWidgets.QHBoxLayout(creators_attrs_top)
        creators_attrs_top_layout.setContentsMargins(0, 0, 0, 0)
        creators_attrs_top_layout.addWidget(creator_basics_widget, 1)
        creators_attrs_top_layout.addWidget(thumbnail_widget, 0)

        # Precreate attributes widget
        pre_create_widget = PreCreateWidget(creators_attrs_widget)

        # Create button
        create_btn_wrapper = QtWidgets.QWidget(creators_attrs_widget)
        create_btn = CreateBtn(create_btn_wrapper)
        create_btn.setEnabled(False)

        create_btn_wrap_layout = QtWidgets.QHBoxLayout(create_btn_wrapper)
        create_btn_wrap_layout.setContentsMargins(0, 0, 0, 0)
        create_btn_wrap_layout.addStretch(1)
        create_btn_wrap_layout.addWidget(create_btn, 0)

        creators_attrs_layout = QtWidgets.QVBoxLayout(creators_attrs_widget)
        creators_attrs_layout.setContentsMargins(0, 0, 0, 0)
        creators_attrs_layout.addWidget(creators_attrs_top, 0)
        creators_attrs_layout.addWidget(pre_create_widget, 1)
        creators_attrs_layout.addWidget(create_btn_wrapper, 0)

        creators_splitter.addWidget(creators_view_widget)
        creators_splitter.addWidget(creators_attrs_widget)
        creators_splitter.setStretchFactor(0, 1)
        creators_splitter.setStretchFactor(1, 2)

        creators_layout = QtWidgets.QVBoxLayout(creators_widget)
        creators_layout.setContentsMargins(0, 0, 0, 0)
        creators_layout.addWidget(creator_short_desc_widget, 0)
        creators_layout.addWidget(attr_separator_widget, 0)
        creators_layout.addWidget(creators_splitter, 1)
        # ------------

        # --- Detailed information about creator ---
        # Detailed description of creator
        # TODO this has no way how can be showed now

        # -------------------------------------------
        main_splitter_widget.addWidget(context_widget)
        main_splitter_widget.addWidget(creators_widget)
        main_splitter_widget.setStretchFactor(0, 1)
        main_splitter_widget.setStretchFactor(1, 3)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(main_splitter_widget, 1)

        prereq_timer = QtCore.QTimer()
        prereq_timer.setInterval(50)
        prereq_timer.setSingleShot(True)

        prereq_timer.timeout.connect(self._invalidate_prereq)

        create_btn.clicked.connect(self._on_create)
        variant_widget.resized.connect(self._on_variant_widget_resize)
        creator_basics_widget.resized.connect(self._on_creator_basics_resize)
        variant_input.returnPressed.connect(self._on_create)
        variant_input.textChanged.connect(self._on_variant_change)
        creators_view.selectionModel().currentChanged.connect(
            self._on_creator_item_change
        )
        variant_hints_btn.clicked.connect(self._on_variant_btn_click)
        variant_hints_menu.triggered.connect(self._on_variant_action)
        assets_widget.selection_changed.connect(self._on_asset_change)
        assets_widget.current_context_required.connect(
            self._on_current_session_context_request
        )
        tasks_widget.task_changed.connect(self._on_task_change)
        thumbnail_widget.thumbnail_created.connect(self._on_thumbnail_create)
        thumbnail_widget.thumbnail_cleared.connect(self._on_thumbnail_clear)

        controller.event_system.add_callback(
            "main.window.closed", self._on_main_window_close
        )
        controller.event_system.add_callback(
            "plugins.refresh.finished", self._on_plugins_refresh
        )

        self._main_splitter_widget = main_splitter_widget

        self._creators_splitter = creators_splitter

        self._context_widget = context_widget
        self._assets_widget = assets_widget
        self._tasks_widget = tasks_widget

        self.subset_name_input = subset_name_input

        self.variant_input = variant_input
        self.variant_hints_btn = variant_hints_btn
        self.variant_hints_menu = variant_hints_menu
        self.variant_hints_group = variant_hints_group

        self._creators_model = creators_model
        self._creators_sort_model = creators_sort_model
        self._creators_view = creators_view
        self._create_btn = create_btn

        self._creator_short_desc_widget = creator_short_desc_widget
        self._creator_basics_widget = creator_basics_widget
        self._thumbnail_widget = thumbnail_widget
        self._pre_create_widget = pre_create_widget
        self._attr_separator_widget = attr_separator_widget

        self._prereq_timer = prereq_timer
        self._first_show = True
        self._last_thumbnail_path = None

        self._last_current_context_asset = None
        self._last_current_context_task = None
        self._use_current_context = True

    @property
    def current_asset_name(self):
        return self._controller.current_asset_name

    @property
    def current_task_name(self):
        return self._controller.current_task_name

    def _context_change_is_enabled(self):
        return self._context_widget.isEnabled()

    def _get_asset_name(self):
        asset_name = None
        if self._context_change_is_enabled():
            asset_name = self._assets_widget.get_selected_asset_name()

        if asset_name is None:
            asset_name = self.current_asset_name
        return asset_name or None

    def _get_task_name(self):
        task_name = None
        if self._context_change_is_enabled():
            # Don't use selection of task if asset is not set
            asset_name = self._assets_widget.get_selected_asset_name()
            if asset_name:
                task_name = self._tasks_widget.get_selected_task_name()

        if not task_name:
            task_name = self.current_task_name
        return task_name

    def _set_context_enabled(self, enabled):
        self._assets_widget.set_enabled(enabled)
        self._tasks_widget.set_enabled(enabled)
        check_prereq = self._context_widget.isEnabled() != enabled
        self._context_widget.setEnabled(enabled)
        if check_prereq:
            self._invalidate_prereq()

    def _on_main_window_close(self):
        """Publisher window was closed."""

        # Use current context on next refresh
        self._use_current_context = True

    def refresh(self):
        current_asset_name = self._controller.current_asset_name
        current_task_name = self._controller.current_task_name

        # Get context before refresh to keep selection of asset and
        #   task widgets
        asset_name = self._get_asset_name()
        task_name = self._get_task_name()

        # Replace by current context if last loaded context was
        #   'current context' before reset
        if (
            self._use_current_context
            or (
                self._last_current_context_asset
                and asset_name == self._last_current_context_asset
                and task_name == self._last_current_context_task
            )
        ):
            asset_name = current_asset_name
            task_name = current_task_name

        # Store values for future refresh
        self._last_current_context_asset = current_asset_name
        self._last_current_context_task = current_task_name
        self._use_current_context = False

        self._prereq_available = False

        # Disable context widget so refresh of asset will use context asset
        #   name
        self._set_context_enabled(False)

        self._assets_widget.refresh()

        # Refresh data before update of creators
        self._refresh_asset()
        # Then refresh creators which may trigger callbacks using refreshed
        #   data
        self._refresh_creators()

        self._assets_widget.update_current_asset()
        self._assets_widget.select_asset_by_name(asset_name)
        self._tasks_widget.set_asset_name(asset_name)
        self._tasks_widget.select_task_name(task_name)

        self._invalidate_prereq_deffered()

    def _invalidate_prereq_deffered(self):
        self._prereq_timer.start()

    def _invalidate_prereq(self):
        prereq_available = True
        creator_btn_tooltips = []

        available_creators = self._creators_model.rowCount() > 0
        if available_creators != self._creators_view.isEnabled():
            self._creators_view.setEnabled(available_creators)

        if not available_creators:
            prereq_available = False
            creator_btn_tooltips.append("Creator is not selected")

        if (
            self._context_change_is_enabled()
            and self._get_asset_name() is None
        ):
            # QUESTION how to handle invalid asset?
            prereq_available = False
            creator_btn_tooltips.append("Context is not selected")

        if prereq_available != self._prereq_available:
            self._prereq_available = prereq_available

            self._create_btn.setEnabled(prereq_available)

            self.variant_input.setEnabled(prereq_available)
            self.variant_hints_btn.setEnabled(prereq_available)

        tooltip = ""
        if creator_btn_tooltips:
            tooltip = "\n".join(creator_btn_tooltips)
        self._create_btn.setToolTip(tooltip)

        self._on_variant_change()

    def _refresh_asset(self):
        asset_name = self._get_asset_name()

        # Skip if asset did not change
        if self._asset_name and self._asset_name == asset_name:
            return

        # Make sure `_asset_name` and `_subset_names` variables are reset
        self._asset_name = asset_name
        self._subset_names = None
        if asset_name is None:
            return

        subset_names = self._controller.get_existing_subset_names(asset_name)

        self._subset_names = subset_names
        if subset_names is None:
            self.subset_name_input.setText("< Asset is not set >")

    def _refresh_creators(self):
        # Refresh creators and add their families to list
        existing_items = {}
        old_creators = set()
        for row in range(self._creators_model.rowCount()):
            item = self._creators_model.item(row, 0)
            identifier = item.data(CREATOR_IDENTIFIER_ROLE)
            existing_items[identifier] = item
            old_creators.add(identifier)

        # Add new families
        new_creators = set()
        creator_items_by_identifier = self._controller.creator_items
        for identifier, creator_item in creator_items_by_identifier.items():
            if creator_item.creator_type != "artist":
                continue

            # TODO add details about creator
            new_creators.add(identifier)
            if identifier in existing_items:
                is_new = False
                item = existing_items[identifier]
            else:
                is_new = True
                item = QtGui.QStandardItem()
                item.setFlags(
                    QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
                )

            item.setData(creator_item.label, QtCore.Qt.DisplayRole)
            item.setData(creator_item.show_order, CREATOR_SORT_ROLE)
            item.setData(identifier, CREATOR_IDENTIFIER_ROLE)
            item.setData(
                creator_item.create_allow_thumbnail,
                CREATOR_THUMBNAIL_ENABLED_ROLE
            )
            item.setData(creator_item.family, FAMILY_ROLE)
            if is_new:
                self._creators_model.appendRow(item)

        # Remove families that are no more available
        for identifier in (old_creators - new_creators):
            item = existing_items[identifier]
            self._creators_model.takeRow(item.row())

        if self._creators_model.rowCount() < 1:
            return

        self._creators_sort_model.sort(0)
        # Make sure there is a selection
        indexes = self._creators_view.selectedIndexes()
        if not indexes:
            index = self._creators_sort_model.index(0, 0)
            self._creators_view.setCurrentIndex(index)
        else:
            index = indexes[0]

        identifier = index.data(CREATOR_IDENTIFIER_ROLE)
        create_item = creator_items_by_identifier.get(identifier)

        self._set_creator(create_item)

    def _on_plugins_refresh(self):
        # Trigger refresh only if is visible
        self.refresh()

    def _on_asset_change(self):
        self._refresh_asset()

        asset_name = self._assets_widget.get_selected_asset_name()
        self._tasks_widget.set_asset_name(asset_name)
        if self._context_change_is_enabled():
            self._invalidate_prereq_deffered()

    def _on_task_change(self):
        if self._context_change_is_enabled():
            self._invalidate_prereq_deffered()

    def _on_thumbnail_create(self, thumbnail_path):
        self._last_thumbnail_path = thumbnail_path
        self._thumbnail_widget.set_current_thumbnails([thumbnail_path])

    def _on_thumbnail_clear(self):
        self._last_thumbnail_path = None

    def _on_current_session_context_request(self):
        self._assets_widget.set_current_session_asset()
        task_name = self.current_task_name
        if task_name:
            self._tasks_widget.select_task_name(task_name)

    def _on_creator_item_change(self, new_index, _old_index):
        identifier = None
        if new_index.isValid():
            identifier = new_index.data(CREATOR_IDENTIFIER_ROLE)
        self._set_creator_by_identifier(identifier)

    def _set_creator_detailed_text(self, creator_item):
        # TODO implement
        description = ""
        if creator_item is not None:
            description = creator_item.detailed_description or description
        self._controller.event_system.emit(
            "show.detailed.help",
            {
                "message": description
            },
            "create.widget"
        )

    def _set_creator_by_identifier(self, identifier):
        creator_item = self._controller.creator_items.get(identifier)
        self._set_creator(creator_item)

    def _set_creator(self, creator_item):
        """Set current creator item.

        Args:
            creator_item (CreatorItem): Item representing creator that can be
                triggered by artist.
        """

        self._creator_short_desc_widget.set_creator_item(creator_item)
        self._set_creator_detailed_text(creator_item)
        self._pre_create_widget.set_creator_item(creator_item)

        self._selected_creator = creator_item

        if not creator_item:
            self._set_context_enabled(False)
            return

        if (
            creator_item.create_allow_context_change
            != self._context_change_is_enabled()
        ):
            self._set_context_enabled(creator_item.create_allow_context_change)
            self._refresh_asset()

        self._thumbnail_widget.setVisible(
            creator_item.create_allow_thumbnail
        )

        default_variants = creator_item.default_variants
        if not default_variants:
            default_variants = [DEFAULT_VARIANT_VALUE]

        default_variant = creator_item.default_variant
        if not default_variant:
            default_variant = default_variants[0]

        for action in tuple(self.variant_hints_menu.actions()):
            self.variant_hints_menu.removeAction(action)
            action.deleteLater()

        for variant in default_variants:
            if variant in SEPARATORS:
                self.variant_hints_menu.addSeparator()
            elif variant:
                self.variant_hints_menu.addAction(variant)

        variant_text = default_variant or DEFAULT_VARIANT_VALUE
        # Make sure subset name is updated to new plugin
        if variant_text == self.variant_input.text():
            self._on_variant_change()
        else:
            self.variant_input.setText(variant_text)

    def _on_variant_widget_resize(self):
        self.variant_hints_btn.setFixedHeight(self.variant_input.height())

    def _on_variant_btn_click(self):
        pos = self.variant_hints_btn.rect().bottomLeft()
        point = self.variant_hints_btn.mapToGlobal(pos)
        self.variant_hints_menu.popup(point)

    def _on_variant_action(self, action):
        value = action.text()
        if self.variant_input.text() != value:
            self.variant_input.setText(value)

    def _on_variant_change(self, variant_value=None):
        if not self._prereq_available:
            return

        # This should probably never happen?
        if not self._selected_creator:
            if self.subset_name_input.text():
                self.subset_name_input.setText("")
            return

        if variant_value is None:
            variant_value = self.variant_input.text()

        if not self._compiled_name_pattern.match(variant_value):
            self._create_btn.setEnabled(False)
            self._set_variant_state_property("invalid")
            self.subset_name_input.setText("< Invalid variant >")
            return

        if not self._context_change_is_enabled():
            self._create_btn.setEnabled(True)
            self._set_variant_state_property("")
            self.subset_name_input.setText("< Valid variant >")
            return

        asset_name = self._get_asset_name()
        task_name = self._get_task_name()
        creator_idenfier = self._selected_creator.identifier
        # Calculate subset name with Creator plugin
        try:
            subset_name = self._controller.get_subset_name(
                creator_idenfier, variant_value, task_name, asset_name
            )
        except TaskNotSetError:
            self._create_btn.setEnabled(False)
            self._set_variant_state_property("invalid")
            self.subset_name_input.setText("< Missing task >")
            return

        self.subset_name_input.setText(subset_name)

        self._create_btn.setEnabled(True)
        self._validate_subset_name(subset_name, variant_value)

    def _validate_subset_name(self, subset_name, variant_value):
        # Get all subsets of the current asset
        if self._subset_names:
            existing_subset_names = set(self._subset_names)
        else:
            existing_subset_names = set()
        existing_subset_names_low = set(
            _name.lower()
            for _name in existing_subset_names
        )

        # Replace
        compare_regex = re.compile(re.sub(
            variant_value, "(.+)", subset_name, flags=re.IGNORECASE
        ))
        variant_hints = set()
        if variant_value:
            for _name in existing_subset_names:
                _result = compare_regex.search(_name)
                if _result:
                    variant_hints |= set(_result.groups())

        # Remove previous hints from menu
        for action in tuple(self.variant_hints_group.actions()):
            self.variant_hints_group.removeAction(action)
            self.variant_hints_menu.removeAction(action)
            action.deleteLater()

        # Add separator if there are hints and menu already has actions
        if variant_hints and self.variant_hints_menu.actions():
            self.variant_hints_menu.addSeparator()

        # Add hints to actions
        for variant_hint in variant_hints:
            action = self.variant_hints_menu.addAction(variant_hint)
            self.variant_hints_group.addAction(action)

        # Indicate subset existence
        if not variant_value:
            property_value = "empty"

        elif subset_name.lower() in existing_subset_names_low:
            # validate existence of subset name with lowered text
            #   - "renderMain" vs. "rendermain" mean same path item for
            #   windows
            property_value = "exists"
        else:
            property_value = "new"

        self._set_variant_state_property(property_value)

        variant_is_valid = variant_value.strip() != ""
        if variant_is_valid != self._create_btn.isEnabled():
            self._create_btn.setEnabled(variant_is_valid)

    def _set_variant_state_property(self, state):
        current_value = self.variant_input.property("state")
        if current_value != state:
            self.variant_input.setProperty("state", state)
            self.variant_input.style().polish(self.variant_input)

    def _on_first_show(self):
        width = self.width()
        part = int(width / 4)
        rem_width = width - part
        self._main_splitter_widget.setSizes([part, rem_width])
        rem_width = rem_width - part
        self._creators_splitter.setSizes([part, rem_width])

    def showEvent(self, event):
        super(CreateWidget, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            self._on_first_show()

    def _on_creator_basics_resize(self):
        self._thumbnail_widget.set_height(
            self._creator_basics_widget.sizeHint().height()
        )

    def _on_create(self):
        indexes = self._creators_view.selectedIndexes()
        if not indexes or len(indexes) > 1:
            return

        if not self._create_btn.isEnabled():
            return

        index = indexes[0]
        creator_identifier = index.data(CREATOR_IDENTIFIER_ROLE)
        family = index.data(FAMILY_ROLE)
        variant = self.variant_input.text()
        # Care about subset name only if context change is enabled
        subset_name = None
        asset_name = None
        task_name = None
        if self._context_change_is_enabled():
            subset_name = self.subset_name_input.text()
            asset_name = self._get_asset_name()
            task_name = self._get_task_name()

        pre_create_data = self._pre_create_widget.current_value()
        if index.data(CREATOR_THUMBNAIL_ENABLED_ROLE):
            pre_create_data[PRE_CREATE_THUMBNAIL_KEY] = (
                self._last_thumbnail_path
            )

        # Where to define these data?
        # - what data show be stored?
        if AYON_SERVER_ENABLED:
            asset_key = "folderPath"
        else:
            asset_key = "asset"

        instance_data = {
            asset_key: asset_name,
            "task": task_name,
            "variant": variant,
            "family": family
        }

        success = self._controller.create(
            creator_identifier,
            subset_name,
            instance_data,
            pre_create_data
        )

        if success:
            self._set_creator(self._selected_creator)
            self.variant_input.setText(variant)
            self._controller.emit_card_message("Creation finished...")
            self._last_thumbnail_path = None
            self._thumbnail_widget.set_current_thumbnails()
