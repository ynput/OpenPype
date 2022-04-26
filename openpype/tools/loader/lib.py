import inspect
from Qt import QtGui
import qtawesome

from openpype.tools.utils.widgets import (
    OptionalAction,
    OptionDialog
)


def change_visibility(model, view, column_name, visible):
    """
        Hides or shows particular 'column_name'.

        "asset" and "subset" columns should be visible only in multiselect
    """
    index = model.Columns.index(column_name)
    view.setColumnHidden(index, not visible)


def get_options(action, loader, parent, repre_contexts):
    """Provides dialog to select value from loader provided options.

        Loader can provide static or dynamically created options based on
        qargparse variants.

        Args:
            action (OptionalAction) - action in menu
            loader (cls of api.Loader) - not initialized yet
            parent (Qt element to parent dialog to)
            repre_contexts (list) of dict with full info about selected repres
        Returns:
            (dict) - selected value from OptionDialog
            None when dialog was closed or cancelled, in all other cases {}
              if no options
    """
    # Pop option dialog
    options = {}
    loader_options = loader.get_options(repre_contexts)
    if getattr(action, "optioned", False) and loader_options:
        dialog = OptionDialog(parent)
        dialog.setWindowTitle(action.label + " Options")
        dialog.create(loader_options)

        if not dialog.exec_():
            return None

        # Get option
        options = dialog.parse()

    return options


def add_representation_loaders_to_menu(loaders, menu, repre_contexts):
    """
        Loops through provider loaders and adds them to 'menu'.

        Expects loaders sorted in requested order.
        Expects loaders de-duplicated if wanted.

        Args:
            loaders(tuple): representation - loader
            menu (OptionalMenu):
            repre_contexts (dict): full info about representations (contains
                their repre_doc, asset_doc, subset_doc, version_doc),
                keys are repre_ids

        Returns:
            menu (OptionalMenu): with new items
    """
    # List the available loaders
    for representation, loader in loaders:
        label = None
        repre_context = None
        if representation:
            label = representation.get("custom_label")
            repre_context = repre_contexts[representation["_id"]]

        if not label:
            label = get_label_from_loader(loader, representation)

        icon = get_icon_from_loader(loader)

        loader_options = loader.get_options([repre_context])

        use_option = bool(loader_options)
        action = OptionalAction(label, icon, use_option, menu)
        if use_option:
            # Add option box tip
            action.set_option_tip(loader_options)

        action.setData((representation, loader))

        # Add tooltip and statustip from Loader docstring
        tip = inspect.getdoc(loader)
        if tip:
            action.setToolTip(tip)
            action.setStatusTip(tip)

        menu.addAction(action)

    return menu


def remove_tool_name_from_loaders(available_loaders, tool_name):
    if not tool_name:
        return available_loaders
    filtered_loaders = []
    for loader in available_loaders:
        if hasattr(loader, "tool_names"):
            if not ("*" in loader.tool_names or
                    tool_name in loader.tool_names):
                continue
        filtered_loaders.append(loader)
    return filtered_loaders


def get_icon_from_loader(loader):
    """Pull icon info from loader class"""
    # Support font-awesome icons using the `.icon` and `.color`
    # attributes on plug-ins.
    icon = getattr(loader, "icon", None)
    if icon is not None:
        try:
            key = "fa.{0}".format(icon)
            color = getattr(loader, "color", "white")
            icon = qtawesome.icon(key, color=color)
        except Exception as e:
            print("Unable to set icon for loader "
                  "{}: {}".format(loader, e))
            icon = None
    return icon


def get_label_from_loader(loader, representation=None):
    """Pull label info from loader class"""
    label = getattr(loader, "label", None)
    if label is None:
        label = loader.__name__
    if representation:
        # Add the representation as suffix
        label = "{0} ({1})".format(label, representation['name'])
    return label


def get_no_loader_action(menu, one_item_selected=False):
    """Creates dummy no loader option in 'menu'"""
    submsg = "your selection."
    if one_item_selected:
        submsg = "this version."
    msg = "No compatible loaders for {}".format(submsg)
    print(msg)
    icon = qtawesome.icon(
        "fa.exclamation",
        color=QtGui.QColor(255, 51, 0)
    )
    action = OptionalAction(("*" + msg), icon, False, menu)
    return action


def sort_loaders(loaders, custom_sorter=None):
    def sorter(value):
        """Sort the Loaders by their order and then their name"""
        Plugin = value[1]
        return Plugin.order, Plugin.__name__

    if not custom_sorter:
        custom_sorter = sorter

    return sorted(loaders, key=custom_sorter)
