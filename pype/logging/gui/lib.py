import contextlib
from Qt import QtCore


def _iter_model_rows(
    model, column, include_root=False
):
    """Iterate over all row indices in a model"""
    indices = [QtCore.QModelIndex()]  # start iteration at root

    for index in indices:
        # Add children to the iterations
        child_rows = model.rowCount(index)
        for child_row in range(child_rows):
            child_index = model.index(child_row, column, index)
            indices.append(child_index)

        if not include_root and not index.isValid():
            continue

        yield index


@contextlib.contextmanager
def preserve_states(
    tree_view, column=0, role=None,
    preserve_expanded=True, preserve_selection=True,
    expanded_role=QtCore.Qt.DisplayRole, selection_role=QtCore.Qt.DisplayRole

):
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
    # When `role` is set then override both expanded and selection roles
    if role:
        expanded_role = role
        selection_role = role

    model = tree_view.model()
    selection_model = tree_view.selectionModel()
    flags = selection_model.Select | selection_model.Rows

    expanded = set()

    if preserve_expanded:
        for index in _iter_model_rows(
            model, column=column, include_root=False
        ):
            if tree_view.isExpanded(index):
                value = index.data(expanded_role)
                expanded.add(value)

    selected = None

    if preserve_selection:
        selected_rows = selection_model.selectedRows()
        if selected_rows:
            selected = set(row.data(selection_role) for row in selected_rows)

    try:
        yield
    finally:
        if expanded:
            for index in _iter_model_rows(
                model, column=0, include_root=False
            ):
                value = index.data(expanded_role)
                is_expanded = value in expanded
                # skip if new index was created meanwhile
                if is_expanded is None:
                    continue
                tree_view.setExpanded(index, is_expanded)

        if selected:
            # Go through all indices, select the ones with similar data
            for index in _iter_model_rows(
                model, column=column, include_root=False
            ):
                value = index.data(selection_role)
                state = value in selected
                if state:
                    tree_view.scrollTo(index)  # Ensure item is visible
                    selection_model.select(index, flags)
