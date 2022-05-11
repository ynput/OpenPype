from Qt import QtWidgets, QtCore, QtGui

from . import (
    ProjectModel,
    ProjectProxyFilter,

    HierarchyModel,
    HierarchySelectionModel,
    HierarchyView,

    CreateProjectDialog,
    PROJECT_NAME_ROLE
)
from .widgets import ConfirmProjectDeletion
from .style import ResourceCache
from openpype.style import load_stylesheet
from openpype.lib import is_admin_password_required
from openpype.widgets import PasswordDialog
from openpype.pipeline import AvalonMongoDB

from openpype import resources
from openpype.api import (
    get_project_basic_paths,
    create_project_folders,
    Logger
)


class ProjectManagerWindow(QtWidgets.QWidget):
    """Main widget of Project Manager tool."""

    def __init__(self, parent=None):
        super(ProjectManagerWindow, self).__init__(parent)

        self.log = Logger.get_logger(self.__class__.__name__)

        self._initial_reset = False
        self._password_dialog = None
        self._user_passed = False

        self.setWindowTitle("OpenPype Project Manager")
        self.setWindowIcon(QtGui.QIcon(resources.get_openpype_icon_filepath()))

        # Top part of window
        top_part_widget = QtWidgets.QWidget(self)

        # Project selection
        project_widget = QtWidgets.QWidget(top_part_widget)

        dbcon = AvalonMongoDB()

        project_model = ProjectModel(dbcon)
        project_proxy = ProjectProxyFilter()
        project_proxy.setSourceModel(project_model)
        project_proxy.setDynamicSortFilter(True)

        project_combobox = QtWidgets.QComboBox(project_widget)
        project_combobox.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToContents
        )
        project_combobox.setModel(project_proxy)
        project_combobox.setRootModelIndex(QtCore.QModelIndex())
        style_delegate = QtWidgets.QStyledItemDelegate()
        project_combobox.setItemDelegate(style_delegate)

        refresh_projects_btn = QtWidgets.QPushButton(project_widget)
        refresh_projects_btn.setIcon(ResourceCache.get_icon("refresh"))
        refresh_projects_btn.setToolTip("Refresh projects")
        refresh_projects_btn.setObjectName("IconBtn")

        create_project_btn = QtWidgets.QPushButton(
            "Create project...", project_widget
        )
        create_folders_btn = QtWidgets.QPushButton(
            ResourceCache.get_icon("asset", "default"),
            "Create Starting Folders",
            project_widget
        )
        create_folders_btn.setEnabled(False)

        remove_projects_btn = QtWidgets.QPushButton(
            "Delete project", project_widget
        )
        remove_projects_btn.setIcon(ResourceCache.get_icon("remove"))
        remove_projects_btn.setObjectName("IconBtn")

        project_layout = QtWidgets.QHBoxLayout(project_widget)
        project_layout.setContentsMargins(0, 0, 0, 0)
        project_layout.addWidget(project_combobox, 0)
        project_layout.addWidget(refresh_projects_btn, 0)
        project_layout.addWidget(create_project_btn, 0)
        project_layout.addWidget(create_folders_btn)
        project_layout.addStretch(1)
        project_layout.addWidget(remove_projects_btn)

        # Helper buttons
        helper_btns_widget = QtWidgets.QWidget(top_part_widget)

        helper_label = QtWidgets.QLabel("Add:", helper_btns_widget)
        add_asset_btn = QtWidgets.QPushButton(
            ResourceCache.get_icon("asset", "default"),
            "Asset",
            helper_btns_widget
        )
        add_task_btn = QtWidgets.QPushButton(
            ResourceCache.get_icon("task", "default"),
            "Task",
            helper_btns_widget
        )
        add_asset_btn.setObjectName("IconBtn")
        add_asset_btn.setEnabled(False)
        add_task_btn.setObjectName("IconBtn")
        add_task_btn.setEnabled(False)

        helper_btns_layout = QtWidgets.QHBoxLayout(helper_btns_widget)
        helper_btns_layout.setContentsMargins(0, 0, 0, 0)
        helper_btns_layout.addWidget(helper_label)
        helper_btns_layout.addWidget(add_asset_btn)
        helper_btns_layout.addWidget(add_task_btn)
        helper_btns_layout.addStretch(1)

        # Add widgets to top widget layout
        top_part_layout = QtWidgets.QVBoxLayout(top_part_widget)
        top_part_layout.setContentsMargins(0, 0, 0, 0)
        top_part_layout.addWidget(project_widget)
        top_part_layout.addWidget(helper_btns_widget)

        hierarchy_model = HierarchyModel(dbcon)

        hierarchy_view = HierarchyView(dbcon, hierarchy_model, self)
        hierarchy_view.setModel(hierarchy_model)

        _selection_model = HierarchySelectionModel(
            hierarchy_model.multiselection_column_indexes
        )
        _selection_model.setModel(hierarchy_view.model())
        hierarchy_view.setSelectionModel(_selection_model)

        buttons_widget = QtWidgets.QWidget(self)

        message_label = QtWidgets.QLabel(buttons_widget)
        save_btn = QtWidgets.QPushButton("Save", buttons_widget)
        save_btn.setEnabled(False)

        buttons_layout = QtWidgets.QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.addWidget(message_label)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(save_btn)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(top_part_widget)
        main_layout.addWidget(hierarchy_view)
        main_layout.addWidget(buttons_widget)

        refresh_projects_btn.clicked.connect(self._on_project_refresh)
        create_project_btn.clicked.connect(self._on_project_create)
        create_folders_btn.clicked.connect(self._on_create_folders)
        remove_projects_btn.clicked.connect(self._on_remove_project)
        project_combobox.currentIndexChanged.connect(self._on_project_change)
        save_btn.clicked.connect(self._on_save_click)
        add_asset_btn.clicked.connect(self._on_add_asset)
        add_task_btn.clicked.connect(self._on_add_task)

        self._dbcon = dbcon
        self._project_model = project_model
        self._project_proxy_model = project_proxy

        self.hierarchy_view = hierarchy_view
        self.hierarchy_model = hierarchy_model

        self.message_label = message_label

        self._refresh_projects_btn = refresh_projects_btn
        self._project_combobox = project_combobox
        self._create_project_btn = create_project_btn
        self._create_folders_btn = create_folders_btn
        self._remove_projects_btn = remove_projects_btn
        self._save_btn = save_btn

        self._add_asset_btn = add_asset_btn
        self._add_task_btn = add_task_btn

        self.resize(1200, 600)
        self.setStyleSheet(load_stylesheet())

    def _set_project(self, project_name=None):
        self._create_folders_btn.setEnabled(project_name is not None)
        self._remove_projects_btn.setEnabled(project_name is not None)
        self._add_asset_btn.setEnabled(project_name is not None)
        self._add_task_btn.setEnabled(project_name is not None)
        self._save_btn.setEnabled(project_name is not None)
        self._project_proxy_model.set_filter_default(project_name is not None)
        self.hierarchy_view.set_project(project_name)

    def _current_project(self):
        row = self._project_combobox.currentIndex()
        if row < 0:
            return None
        index = self._project_proxy_model.index(row, 0)
        return index.data(PROJECT_NAME_ROLE)

    def showEvent(self, event):
        super(ProjectManagerWindow, self).showEvent(event)

        if not self._initial_reset:
            self.reset()

        font_size = self._refresh_projects_btn.fontMetrics().height()
        icon_size = QtCore.QSize(font_size, font_size)
        self._refresh_projects_btn.setIconSize(icon_size)
        self._add_asset_btn.setIconSize(icon_size)
        self._add_task_btn.setIconSize(icon_size)

    def refresh_projects(self, project_name=None):
        if project_name is None:
            if self._project_combobox.count() > 0:
                project_name = self._project_combobox.currentText()

        self._project_model.refresh()
        self._project_proxy_model.sort(0, QtCore.Qt.AscendingOrder)

        if self._project_combobox.count() == 0:
            return self._set_project()

        if project_name:
            row = self._project_combobox.findText(project_name)
            if row >= 0:
                self._project_combobox.setCurrentIndex(row)

        selected_project = self._current_project()
        self._set_project(selected_project)

    def _on_project_change(self):
        selected_project = self._current_project()
        self._set_project(selected_project)

    def _on_project_refresh(self):
        self.refresh_projects()

    def _on_save_click(self):
        self.hierarchy_model.save()

    def _on_add_asset(self):
        self.hierarchy_view.add_asset()

    def _on_add_task(self):
        self.hierarchy_view.add_task()

    def _on_create_folders(self):
        project_name = self._current_project()
        if not project_name:
            return

        qm = QtWidgets.QMessageBox
        ans = qm.question(self,
                          "OpenPype Project Manager",
                          "Confirm to create starting project folders?",
                          qm.Yes | qm.No)
        if ans == qm.Yes:
            try:
                # Get paths based on presets
                basic_paths = get_project_basic_paths(project_name)
                if not basic_paths:
                    pass
                # Invoking OpenPype API to create the project folders
                create_project_folders(basic_paths, project_name)
            except Exception as exc:
                self.log.warning(
                    "Cannot create starting folders: {}".format(exc),
                    exc_info=True
                )

    def _on_remove_project(self):
        project_name = self._current_project()
        dialog = ConfirmProjectDeletion(project_name, self)
        result = dialog.exec_()
        if result != 1:
            return

        database = self._dbcon.database
        if project_name in database.collection_names():
            collection = database[project_name]
            collection.drop()
        self.refresh_projects()

    def show_message(self, message):
        # TODO add nicer message pop
        self.message_label.setText(message)

    def _on_project_create(self):
        dialog = CreateProjectDialog(self)
        dialog.exec_()
        if dialog.result() != 1:
            return

        project_name = dialog.project_name
        self.show_message("Created project \"{}\"".format(project_name))
        self.refresh_projects(project_name)

    def _show_password_dialog(self):
        if self._password_dialog:
            self._password_dialog.open()

    def _on_password_dialog_close(self, password_passed):
        # Store result for future settings reset
        self._user_passed = password_passed
        # Remove reference to password dialog
        self._password_dialog = None
        if password_passed:
            self.reset()
        else:
            self.close()

    def reset(self):
        if self._password_dialog:
            return

        if not self._user_passed:
            self._user_passed = not is_admin_password_required()

        if not self._user_passed:
            self.setEnabled(False)
            # Avoid doubled dialog
            dialog = PasswordDialog(self)
            dialog.setModal(True)
            dialog.finished.connect(self._on_password_dialog_close)

            self._password_dialog = dialog

            QtCore.QTimer.singleShot(100, self._show_password_dialog)

            return

        self.setEnabled(True)

        # Mark as was reset
        if not self._initial_reset:
            self._initial_reset = True

        self.refresh_projects()
