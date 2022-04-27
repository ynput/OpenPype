import sys
import re
import traceback
import copy

try:
    import commonmark
except Exception:
    commonmark = None
from Qt import QtWidgets, QtCore, QtGui
from openpype.lib import TaskNotSetError
from openpype.pipeline.create import (
    CreatorError,
    SUBSET_NAME_ALLOWED_SYMBOLS
)

from openpype.tools.utils import ErrorMessageBox

from .widgets import IconValuePixmapLabel
from .assets_widget import CreateDialogAssetsWidget
from .tasks_widget import CreateDialogTasksWidget
from .precreate_widget import PreCreateWidget
from ..constants import (
    VARIANT_TOOLTIP,
    CREATOR_IDENTIFIER_ROLE,
    FAMILY_ROLE
)

SEPARATORS = ("---separator---", "---")


class VariantInputsWidget(QtWidgets.QWidget):
    resized = QtCore.Signal()

    def resizeEvent(self, event):
        super(VariantInputsWidget, self).resizeEvent(event)
        self.resized.emit()


class CreateErrorMessageBox(ErrorMessageBox):
    def __init__(
        self,
        creator_label,
        subset_name,
        asset_name,
        exc_msg,
        formatted_traceback,
        parent
    ):
        self._creator_label = creator_label
        self._subset_name = subset_name
        self._asset_name = asset_name
        self._exc_msg = exc_msg
        self._formatted_traceback = formatted_traceback
        super(CreateErrorMessageBox, self).__init__("Creation failed", parent)

    def _create_top_widget(self, parent_widget):
        label_widget = QtWidgets.QLabel(parent_widget)
        label_widget.setText(
            "<span style='font-size:18pt;'>Failed to create</span>"
        )
        return label_widget

    def _get_report_data(self):
        report_message = (
            "{creator}: Failed to create Subset: \"{subset}\""
            " in Asset: \"{asset}\""
            "\n\nError: {message}"
        ).format(
            creator=self._creator_label,
            subset=self._subset_name,
            asset=self._asset_name,
            message=self._exc_msg,
        )
        if self._formatted_traceback:
            report_message += "\n\n{}".format(self._formatted_traceback)
        return [report_message]

    def _create_content(self, content_layout):
        item_name_template = (
            "<span style='font-weight:bold;'>Creator:</span> {}<br>"
            "<span style='font-weight:bold;'>Subset:</span> {}<br>"
            "<span style='font-weight:bold;'>Asset:</span> {}<br>"
        )
        exc_msg_template = "<span style='font-weight:bold'>{}</span>"

        line = self._create_line()
        content_layout.addWidget(line)

        item_name_widget = QtWidgets.QLabel(self)
        item_name_widget.setText(
            item_name_template.format(
                self._creator_label, self._subset_name, self._asset_name
            )
        )
        content_layout.addWidget(item_name_widget)

        message_label_widget = QtWidgets.QLabel(self)
        message_label_widget.setText(
            exc_msg_template.format(self.convert_text_for_html(self._exc_msg))
        )
        content_layout.addWidget(message_label_widget)

        if self._formatted_traceback:
            line_widget = self._create_line()
            tb_widget = self._create_traceback_widget(
                self._formatted_traceback
            )
            content_layout.addWidget(line_widget)
            content_layout.addWidget(tb_widget)


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

    def set_plugin(self, plugin=None):
        if not plugin:
            self._icon_widget.set_icon_def(None)
            self._family_label.setText("")
            self._description_label.setText("")
            return

        plugin_icon = plugin.get_icon()
        description = plugin.get_description() or ""

        self._icon_widget.set_icon_def(plugin_icon)
        self._family_label.setText("<b>{}</b>".format(plugin.family))
        self._family_label.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self._description_label.setText(description)


class HelpButton(QtWidgets.QPushButton):
    resized = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super(HelpButton, self).__init__(*args, **kwargs)
        self.setObjectName("CreateDialogHelpButton")

        self._expanded = None
        self.set_expanded()

    def set_expanded(self, expanded=None):
        if self._expanded is expanded:
            if expanded is not None:
                return
            expanded = False
        self._expanded = expanded
        if expanded:
            text = "<"
        else:
            text = "?"
        self.setText(text)

        self._update_size()

    def _update_size(self):
        new_size = self.minimumSizeHint()
        if self.size() != new_size:
            self.resize(new_size)
            self.resized.emit()

    def showEvent(self, event):
        super(HelpButton, self).showEvent(event)
        self._update_size()

    def resizeEvent(self, event):
        super(HelpButton, self).resizeEvent(event)
        self._update_size()


class CreateDialog(QtWidgets.QDialog):
    default_size = (900, 500)

    def __init__(
        self, controller, asset_name=None, task_name=None, parent=None
    ):
        super(CreateDialog, self).__init__(parent)

        self.setWindowTitle("Create new instance")

        self.controller = controller

        if asset_name is None:
            asset_name = self.dbcon.Session.get("AVALON_ASSET")

        if task_name is None:
            task_name = self.dbcon.Session.get("AVALON_TASK")

        self._asset_name = asset_name
        self._task_name = task_name

        self._last_pos = None
        self._asset_doc = None
        self._subset_names = None
        self._selected_creator = None

        self._prereq_available = False

        self._message_dialog = None

        name_pattern = "^[{}]*$".format(SUBSET_NAME_ALLOWED_SYMBOLS)
        self._name_pattern = name_pattern
        self._compiled_name_pattern = re.compile(name_pattern)

        context_widget = QtWidgets.QWidget(self)

        assets_widget = CreateDialogAssetsWidget(controller, context_widget)
        tasks_widget = CreateDialogTasksWidget(controller, context_widget)

        context_layout = QtWidgets.QVBoxLayout(context_widget)
        context_layout.setContentsMargins(0, 0, 0, 0)
        context_layout.setSpacing(0)
        context_layout.addWidget(assets_widget, 2)
        context_layout.addWidget(tasks_widget, 1)

        # --- Creators view ---
        creators_view = QtWidgets.QListView(self)
        creators_model = QtGui.QStandardItemModel()
        creators_view.setModel(creators_model)

        variant_widget = VariantInputsWidget(self)

        variant_input = QtWidgets.QLineEdit(variant_widget)
        variant_input.setObjectName("VariantInput")
        variant_input.setToolTip(VARIANT_TOOLTIP)

        variant_hints_btn = QtWidgets.QToolButton(variant_widget)
        variant_hints_btn.setArrowType(QtCore.Qt.DownArrow)
        variant_hints_btn.setIconSize(QtCore.QSize(12, 12))

        variant_hints_menu = QtWidgets.QMenu(variant_widget)
        variant_hints_group = QtWidgets.QActionGroup(variant_hints_menu)
        # variant_hints_btn.setMenu(variant_hints_menu)

        variant_layout = QtWidgets.QHBoxLayout(variant_widget)
        variant_layout.setContentsMargins(0, 0, 0, 0)
        variant_layout.setSpacing(0)
        variant_layout.addWidget(variant_input, 1)
        variant_layout.addWidget(variant_hints_btn, 0, QtCore.Qt.AlignVCenter)

        subset_name_input = QtWidgets.QLineEdit(self)
        subset_name_input.setEnabled(False)

        create_btn = QtWidgets.QPushButton("Create", self)
        create_btn.setEnabled(False)

        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow("Variant:", variant_widget)
        form_layout.addRow("Subset:", subset_name_input)

        mid_widget = QtWidgets.QWidget(self)
        mid_layout = QtWidgets.QVBoxLayout(mid_widget)
        mid_layout.setContentsMargins(0, 0, 0, 0)
        mid_layout.addWidget(QtWidgets.QLabel("Choose family:", self))
        mid_layout.addWidget(creators_view, 1)
        mid_layout.addLayout(form_layout, 0)
        mid_layout.addWidget(create_btn, 0)
        # ------------

        # --- Creator short info and attr defs ---
        creator_attrs_widget = QtWidgets.QWidget(self)

        creator_short_desc_widget = CreatorShortDescWidget(
            creator_attrs_widget
        )

        separator_widget = QtWidgets.QWidget(self)
        separator_widget.setObjectName("Separator")
        separator_widget.setMinimumHeight(2)
        separator_widget.setMaximumHeight(2)

        # Precreate attributes widget
        pre_create_widget = PreCreateWidget(creator_attrs_widget)

        creator_attrs_layout = QtWidgets.QVBoxLayout(creator_attrs_widget)
        creator_attrs_layout.setContentsMargins(0, 0, 0, 0)
        creator_attrs_layout.addWidget(creator_short_desc_widget, 0)
        creator_attrs_layout.addWidget(separator_widget, 0)
        creator_attrs_layout.addWidget(pre_create_widget, 1)
        # -------------------------------------

        # --- Detailed information about creator ---
        # Detailed description of creator
        detail_description_widget = QtWidgets.QTextEdit(self)
        detail_description_widget.setObjectName("InfoText")
        detail_description_widget.setTextInteractionFlags(
            QtCore.Qt.TextBrowserInteraction
        )
        detail_description_widget.setVisible(False)
        # -------------------------------------------

        splitter_widget = QtWidgets.QSplitter(self)
        splitter_widget.addWidget(context_widget)
        splitter_widget.addWidget(mid_widget)
        splitter_widget.addWidget(creator_attrs_widget)
        splitter_widget.addWidget(detail_description_widget)
        splitter_widget.setStretchFactor(0, 1)
        splitter_widget.setStretchFactor(1, 1)
        splitter_widget.setStretchFactor(2, 1)
        splitter_widget.setStretchFactor(3, 1)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(splitter_widget, 1)

        # Floating help button
        help_btn = HelpButton(self)

        prereq_timer = QtCore.QTimer()
        prereq_timer.setInterval(50)
        prereq_timer.setSingleShot(True)

        prereq_timer.timeout.connect(self._on_prereq_timer)

        help_btn.clicked.connect(self._on_help_btn)
        help_btn.resized.connect(self._on_help_btn_resize)

        create_btn.clicked.connect(self._on_create)
        variant_widget.resized.connect(self._on_variant_widget_resize)
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

        controller.add_plugins_refresh_callback(self._on_plugins_refresh)

        self._splitter_widget = splitter_widget

        self._context_widget = context_widget
        self._assets_widget = assets_widget
        self._tasks_widget = tasks_widget

        self.subset_name_input = subset_name_input

        self.variant_input = variant_input
        self.variant_hints_btn = variant_hints_btn
        self.variant_hints_menu = variant_hints_menu
        self.variant_hints_group = variant_hints_group

        self.creators_model = creators_model
        self.creators_view = creators_view
        self.create_btn = create_btn

        self._creator_short_desc_widget = creator_short_desc_widget
        self._pre_create_widget = pre_create_widget
        self._detail_description_widget = detail_description_widget
        self._help_btn = help_btn

        self._prereq_timer = prereq_timer
        self._first_show = True

    def _context_change_is_enabled(self):
        return self._context_widget.isEnabled()

    def _get_asset_name(self):
        asset_name = None
        if self._context_change_is_enabled():
            asset_name = self._assets_widget.get_selected_asset_name()

        if asset_name is None:
            asset_name = self._asset_name
        return asset_name

    def _get_task_name(self):
        task_name = None
        if self._context_change_is_enabled():
            # Don't use selection of task if asset is not set
            asset_name = self._assets_widget.get_selected_asset_name()
            if asset_name:
                task_name = self._tasks_widget.get_selected_task_name()

        if not task_name:
            task_name = self._task_name
        return task_name

    @property
    def dbcon(self):
        return self.controller.dbcon

    def _set_context_enabled(self, enabled):
        self._assets_widget.set_enabled(enabled)
        self._tasks_widget.set_enabled(enabled)
        self._context_widget.setEnabled(enabled)

    def refresh(self):
        # Get context before refresh to keep selection of asset and
        #   task widgets
        asset_name = self._get_asset_name()
        task_name = self._get_task_name()

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

        self._assets_widget.set_current_asset_name(self._asset_name)
        self._assets_widget.select_asset_by_name(asset_name)
        self._tasks_widget.set_asset_name(asset_name)
        self._tasks_widget.select_task_name(task_name)

        self._invalidate_prereq()

    def _invalidate_prereq(self):
        self._prereq_timer.start()

    def _on_prereq_timer(self):
        prereq_available = True
        if self.creators_model.rowCount() < 1:
            prereq_available = False

        if self._asset_doc is None:
            # QUESTION how to handle invalid asset?
            prereq_available = False

        if prereq_available != self._prereq_available:
            self._prereq_available = prereq_available

            self.create_btn.setEnabled(prereq_available)
            self.creators_view.setEnabled(prereq_available)
            self.variant_input.setEnabled(prereq_available)
            self.variant_hints_btn.setEnabled(prereq_available)
        self._on_variant_change()

    def _refresh_asset(self):
        asset_name = self._get_asset_name()

        # Skip if asset did not change
        if self._asset_doc and self._asset_doc["name"] == asset_name:
            return

        # Make sure `_asset_doc` and `_subset_names` variables are reset
        self._asset_doc = None
        self._subset_names = None
        if asset_name is None:
            return

        asset_doc = self.dbcon.find_one({
            "type": "asset",
            "name": asset_name
        })
        self._asset_doc = asset_doc

        if asset_doc:
            subset_docs = self.dbcon.find(
                {
                    "type": "subset",
                    "parent": asset_doc["_id"]
                },
                {"name": 1}
            )
            self._subset_names = set(subset_docs.distinct("name"))

        if not asset_doc:
            self.subset_name_input.setText("< Asset is not set >")

    def _refresh_creators(self):
        # Refresh creators and add their families to list
        existing_items = {}
        old_creators = set()
        for row in range(self.creators_model.rowCount()):
            item = self.creators_model.item(row, 0)
            identifier = item.data(CREATOR_IDENTIFIER_ROLE)
            existing_items[identifier] = item
            old_creators.add(identifier)

        # Add new families
        new_creators = set()
        for identifier, creator in self.controller.manual_creators.items():
            # TODO add details about creator
            new_creators.add(identifier)
            if identifier in existing_items:
                item = existing_items[identifier]
            else:
                item = QtGui.QStandardItem()
                item.setFlags(
                    QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
                )
                self.creators_model.appendRow(item)

            label = creator.label or identifier
            item.setData(label, QtCore.Qt.DisplayRole)
            item.setData(identifier, CREATOR_IDENTIFIER_ROLE)
            item.setData(creator.family, FAMILY_ROLE)

        # Remove families that are no more available
        for identifier in (old_creators - new_creators):
            item = existing_items[identifier]
            self.creators_model.takeRow(item.row())

        if self.creators_model.rowCount() < 1:
            return

        # Make sure there is a selection
        indexes = self.creators_view.selectedIndexes()
        if not indexes:
            index = self.creators_model.index(0, 0)
            self.creators_view.setCurrentIndex(index)
        else:
            index = indexes[0]

        identifier = index.data(CREATOR_IDENTIFIER_ROLE)

        self._set_creator_by_identifier(identifier)

    def _on_plugins_refresh(self):
        # Trigger refresh only if is visible
        if self.isVisible():
            self.refresh()

    def _on_asset_change(self):
        self._refresh_asset()

        asset_name = self._assets_widget.get_selected_asset_name()
        self._tasks_widget.set_asset_name(asset_name)
        if self._context_change_is_enabled():
            self._invalidate_prereq()

    def _on_task_change(self):
        if self._context_change_is_enabled():
            self._invalidate_prereq()

    def _on_current_session_context_request(self):
        self._assets_widget.set_current_session_asset()
        if self._task_name:
            self._tasks_widget.select_task_name(self._task_name)

    def _on_creator_item_change(self, new_index, _old_index):
        identifier = None
        if new_index.isValid():
            identifier = new_index.data(CREATOR_IDENTIFIER_ROLE)
        self._set_creator_by_identifier(identifier)

    def _update_help_btn(self):
        pos_x = self.width() - self._help_btn.width()
        point = self._creator_short_desc_widget.rect().topRight()
        mapped_point = self._creator_short_desc_widget.mapTo(self, point)
        pos_y = mapped_point.y()
        self._help_btn.move(max(0, pos_x), max(0, pos_y))

    def _on_help_btn_resize(self):
        self._update_help_btn()

    def _on_help_btn(self):
        final_size = self.size()
        cur_sizes = self._splitter_widget.sizes()
        spacing = self._splitter_widget.handleWidth()

        sizes = []
        for idx, value in enumerate(cur_sizes):
            if idx < 3:
                sizes.append(value)

        now_visible = self._detail_description_widget.isVisible()
        if now_visible:
            width = final_size.width() - (
                spacing + self._detail_description_widget.width()
            )

        else:
            last_size = self._detail_description_widget.sizeHint().width()
            width = final_size.width() + spacing + last_size
            sizes.append(last_size)

        final_size.setWidth(width)

        self._detail_description_widget.setVisible(not now_visible)
        self._splitter_widget.setSizes(sizes)
        self.resize(final_size)

        self._help_btn.set_expanded(not now_visible)

    def _set_creator_detailed_text(self, creator):
        if not creator:
            self._detail_description_widget.setPlainText("")
            return
        detailed_description = creator.get_detail_description() or ""
        if commonmark:
            html = commonmark.commonmark(detailed_description)
            self._detail_description_widget.setHtml(html)
        else:
            self._detail_description_widget.setMarkdown(detailed_description)

    def _set_creator_by_identifier(self, identifier):
        creator = self.controller.manual_creators.get(identifier)
        self._set_creator(creator)

    def _set_creator(self, creator):
        self._creator_short_desc_widget.set_plugin(creator)
        self._set_creator_detailed_text(creator)
        self._pre_create_widget.set_plugin(creator)

        self._selected_creator = creator

        if not creator:
            self._set_context_enabled(False)
            return

        if (
            creator.create_allow_context_change
            != self._context_change_is_enabled()
        ):
            self._set_context_enabled(creator.create_allow_context_change)
            self._refresh_asset()

        default_variants = creator.get_default_variants()
        if not default_variants:
            default_variants = ["Main"]

        default_variant = creator.get_default_variant()
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

        self.variant_input.setText(default_variant or "Main")

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

        self.create_btn.setEnabled(True)
        if not self._compiled_name_pattern.match(variant_value):
            self.create_btn.setEnabled(False)
            self._set_variant_state_property("invalid")
            self.subset_name_input.setText("< Invalid variant >")
            return

        project_name = self.controller.project_name
        task_name = self._get_task_name()

        asset_doc = copy.deepcopy(self._asset_doc)
        # Calculate subset name with Creator plugin
        try:
            subset_name = self._selected_creator.get_subset_name(
                variant_value, task_name, asset_doc, project_name
            )
        except TaskNotSetError:
            self.create_btn.setEnabled(False)
            self._set_variant_state_property("invalid")
            self.subset_name_input.setText("< Missing task >")
            return

        self.subset_name_input.setText(subset_name)

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
        if variant_is_valid != self.create_btn.isEnabled():
            self.create_btn.setEnabled(variant_is_valid)

    def _set_variant_state_property(self, state):
        current_value = self.variant_input.property("state")
        if current_value != state:
            self.variant_input.setProperty("state", state)
            self.variant_input.style().polish(self.variant_input)

    def moveEvent(self, event):
        super(CreateDialog, self).moveEvent(event)
        self._last_pos = self.pos()

    def showEvent(self, event):
        super(CreateDialog, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            width, height = self.default_size
            self.resize(width, height)

            third_size = int(width / 3)
            self._splitter_widget.setSizes(
                [third_size, third_size, width - (2 * third_size)]
            )

        if self._last_pos is not None:
            self.move(self._last_pos)

        self._update_help_btn()

        self.refresh()

    def resizeEvent(self, event):
        super(CreateDialog, self).resizeEvent(event)
        self._update_help_btn()

    def _on_create(self):
        indexes = self.creators_view.selectedIndexes()
        if not indexes or len(indexes) > 1:
            return

        if not self.create_btn.isEnabled():
            return

        index = indexes[0]
        creator_label = index.data(QtCore.Qt.DisplayRole)
        creator_identifier = index.data(CREATOR_IDENTIFIER_ROLE)
        family = index.data(FAMILY_ROLE)
        subset_name = self.subset_name_input.text()
        variant = self.variant_input.text()
        asset_name = self._get_asset_name()
        task_name = self._get_task_name()
        pre_create_data = self._pre_create_widget.current_value()
        # Where to define these data?
        # - what data show be stored?
        instance_data = {
            "asset": asset_name,
            "task": task_name,
            "variant": variant,
            "family": family
        }

        error_msg = None
        formatted_traceback = None
        try:
            self.controller.create(
                creator_identifier,
                subset_name,
                instance_data,
                pre_create_data
            )

        except CreatorError as exc:
            error_msg = str(exc)

        # Use bare except because some hosts raise their exceptions that
        #   do not inherit from python's `BaseException`
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            formatted_traceback = "".join(traceback.format_exception(
                exc_type, exc_value, exc_traceback
            ))
            error_msg = str(exc_value)

        if error_msg is None:
            self._set_creator(self._selected_creator)
        else:
            box = CreateErrorMessageBox(
                creator_label,
                subset_name,
                asset_name,
                error_msg,
                formatted_traceback,
                parent=self
            )
            box.show()
            # Store dialog so is not garbage collected before is shown
            self._message_dialog = box
