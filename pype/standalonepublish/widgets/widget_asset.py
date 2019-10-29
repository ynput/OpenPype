import contextlib
from . import QtWidgets, QtCore
from . import RecursiveSortFilterProxyModel, AssetModel
from . import qtawesome, style
from . import TasksTemplateModel, DeselectableTreeView
from . import _iter_model_rows

@contextlib.contextmanager
def preserve_expanded_rows(tree_view,
                           column=0,
                           role=QtCore.Qt.DisplayRole):
    """Preserves expanded row in QTreeView by column's data role.

    This function is created to maintain the expand vs collapse status of
    the model items. When refresh is triggered the items which are expanded
    will stay expanded and vise versa.

    Arguments:
        tree_view (QWidgets.QTreeView): the tree view which is
            nested in the application
        column (int): the column to retrieve the data from
        role (int): the role which dictates what will be returned

    Returns:
        None

    """

    model = tree_view.model()

    expanded = set()

    for index in _iter_model_rows(model,
                                  column=column,
                                  include_root=False):
        if tree_view.isExpanded(index):
            value = index.data(role)
            expanded.add(value)

    try:
        yield
    finally:
        if not expanded:
            return

        for index in _iter_model_rows(model,
                                      column=column,
                                      include_root=False):
            value = index.data(role)
            state = value in expanded
            if state:
                tree_view.expand(index)
            else:
                tree_view.collapse(index)


@contextlib.contextmanager
def preserve_selection(tree_view,
                       column=0,
                       role=QtCore.Qt.DisplayRole,
                       current_index=True):
    """Preserves row selection in QTreeView by column's data role.

    This function is created to maintain the selection status of
    the model items. When refresh is triggered the items which are expanded
    will stay expanded and vise versa.

        tree_view (QWidgets.QTreeView): the tree view nested in the application
        column (int): the column to retrieve the data from
        role (int): the role which dictates what will be returned

    Returns:
        None

    """

    model = tree_view.model()
    selection_model = tree_view.selectionModel()
    flags = selection_model.Select | selection_model.Rows

    if current_index:
        current_index_value = tree_view.currentIndex().data(role)
    else:
        current_index_value = None

    selected_rows = selection_model.selectedRows()
    if not selected_rows:
        yield
        return

    selected = set(row.data(role) for row in selected_rows)
    try:
        yield
    finally:
        if not selected:
            return

        # Go through all indices, select the ones with similar data
        for index in _iter_model_rows(model,
                                      column=column,
                                      include_root=False):

            value = index.data(role)
            state = value in selected
            if state:
                tree_view.scrollTo(index)  # Ensure item is visible
                selection_model.select(index, flags)

            if current_index_value and value == current_index_value:
                tree_view.setCurrentIndex(index)


class AssetWidget(QtWidgets.QWidget):
    """A Widget to display a tree of assets with filter

    To list the assets of the active project:
        >>> # widget = AssetWidget()
        >>> # widget.refresh()
        >>> # widget.show()

    """

    assets_refreshed = QtCore.Signal()   # on model refresh
    selection_changed = QtCore.Signal()  # on view selection change
    current_changed = QtCore.Signal()    # on view current index change

    def __init__(self, dbcon, parent=None):
        super(AssetWidget, self).__init__(parent=parent)
        self.setContentsMargins(0, 0, 0, 0)

        self.dbcon = dbcon

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Project
        self.combo_projects = QtWidgets.QComboBox()
        self._set_projects()
        self.combo_projects.currentTextChanged.connect(self.on_project_change)
        # Tree View
        model = AssetModel(dbcon=self.dbcon, parent=self)
        proxy = RecursiveSortFilterProxyModel()
        proxy.setSourceModel(model)
        proxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        view = DeselectableTreeView()
        view.setIndentation(15)
        view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        view.setHeaderHidden(True)
        view.setModel(proxy)

        # Header
        header = QtWidgets.QHBoxLayout()

        icon = qtawesome.icon("fa.refresh", color=style.colors.light)
        refresh = QtWidgets.QPushButton(icon, "")
        refresh.setToolTip("Refresh items")

        filter = QtWidgets.QLineEdit()
        filter.textChanged.connect(proxy.setFilterFixedString)
        filter.setPlaceholderText("Filter assets..")

        header.addWidget(filter)
        header.addWidget(refresh)

        # Layout
        layout.addWidget(self.combo_projects)
        layout.addLayout(header)
        layout.addWidget(view)

        # tasks
        task_view = DeselectableTreeView()
        task_view.setIndentation(0)
        task_view.setHeaderHidden(True)
        task_view.setVisible(False)

        task_model = TasksTemplateModel()
        task_view.setModel(task_model)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)
        main_layout.addLayout(layout, 80)
        main_layout.addWidget(task_view, 20)

        # Signals/Slots
        selection = view.selectionModel()
        selection.selectionChanged.connect(self.selection_changed)
        selection.currentChanged.connect(self.current_changed)
        refresh.clicked.connect(self.refresh)

        self.selection_changed.connect(self._refresh_tasks)

        self.task_view = task_view
        self.task_model = task_model
        self.refreshButton = refresh
        self.model = model
        self.proxy = proxy
        self.view = view

    def collect_data(self):
        project = self.dbcon.find_one({'type': 'project'})
        asset = self.get_active_asset()

        try:
            index = self.task_view.selectedIndexes()[0]
            task = self.task_model.itemData(index)[0]
        except Exception:
            task = None
        data = {
            'project': project['name'],
            'asset': asset['name'],
            'silo': asset.get("silo"),
            'parents': self.get_parents(asset),
            'task': task
        }

        return data

    def get_parents(self, entity):
        ent_parents = entity.get("data", {}).get("parents")
        if ent_parents is not None and isinstance(ent_parents, list):
            return ent_parents

        output = []
        if entity.get('data', {}).get('visualParent', None) is None:
            return output
        parent = self.dbcon.find_one({'_id': entity['data']['visualParent']})
        output.append(parent['name'])
        output.extend(self.get_parents(parent))
        return output

    def _set_projects(self):
        projects = list()
        for project in self.dbcon.projects():
            projects.append(project['name'])

        self.combo_projects.clear()
        if len(projects) > 0:
            self.combo_projects.addItems(projects)
            self.dbcon.activate_project(projects[0])

    def on_project_change(self):
        projects = list()
        for project in self.dbcon.projects():
            projects.append(project['name'])
        project_name = self.combo_projects.currentText()
        if project_name in projects:
            self.dbcon.activate_project(project_name)
        self.refresh()

    def _refresh_model(self):
        with preserve_expanded_rows(
            self.view, column=0, role=self.model.ObjectIdRole
        ):
            with preserve_selection(
                self.view, column=0, role=self.model.ObjectIdRole
            ):
                self.model.refresh()

        self.assets_refreshed.emit()

    def refresh(self):
        self._refresh_model()

    def _refresh_tasks(self):
        tasks = []
        selected = self.get_selected_assets()
        if len(selected) == 1:
            asset = self.dbcon.find_one({
                "_id": selected[0], "type": "asset"
            })
            if asset:
                tasks = asset.get('data', {}).get('tasks', [])
        self.task_model.set_tasks(tasks)
        self.task_view.setVisible(len(tasks)>0)

    def get_active_asset(self):
        """Return the asset id the current asset."""
        current = self.view.currentIndex()
        return current.data(self.model.ItemRole)

    def get_active_index(self):
        return self.view.currentIndex()

    def get_selected_assets(self):
        """Return the assets' ids that are selected."""
        selection = self.view.selectionModel()
        rows = selection.selectedRows()
        return [row.data(self.model.ObjectIdRole) for row in rows]

    def select_assets(self, assets, expand=True, key="name"):
        """Select assets by name.

        Args:
            assets (list): List of asset names
            expand (bool): Whether to also expand to the asset in the view

        Returns:
            None

        """
        # TODO: Instead of individual selection optimize for many assets

        if not isinstance(assets, (tuple, list)):
            assets = [assets]
        assert isinstance(
            assets, (tuple, list)
        ), "Assets must be list or tuple"

        # convert to list - tuple cant be modified
        assets = list(assets)

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
            assets.pop(assets.index(value))

            selection_model.select(index, mode)

            if expand:
                # Expand parent index
                self.view.expand(self.proxy.parent(index))

            # Set the currently active index
            self.view.setCurrentIndex(index)
