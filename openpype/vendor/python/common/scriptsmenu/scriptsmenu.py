import os
import json
import logging
from collections import defaultdict

from .vendor.Qt import QtWidgets, QtCore
from . import action

log = logging.getLogger(__name__)


class ScriptsMenu(QtWidgets.QMenu):
    """A Qt menu that displays a list of searchable actions"""

    updated = QtCore.Signal(QtWidgets.QMenu)

    def __init__(self, *args, **kwargs):
        """Initialize Scripts menu

        Args:
            title (str): the name of the root menu which will be created
        
            parent (QtWidgets.QObject) : the QObject to parent the menu to
        
        Returns:
            None

        """
        QtWidgets.QMenu.__init__(self, *args, **kwargs)

        self.searchbar = None
        self.update_action = None

        self._script_actions = []
        self._callbacks = defaultdict(list)

        # Automatically add it to the parent menu
        parent = kwargs.get("parent", None)
        if parent:
            parent.addMenu(self)

        objectname = kwargs.get("objectName", "scripts")
        title = kwargs.get("title", "Scripts")
        self.setObjectName(objectname)
        self.setTitle(title)

        # add default items in the menu
        self.create_default_items()

    def on_update(self):
        self.updated.emit(self)

    @property
    def registered_callbacks(self):
        return self._callbacks.copy()

    def create_default_items(self):
        """Add a search bar to the top of the menu given"""

        # create widget and link function
        searchbar = QtWidgets.QLineEdit()
        searchbar.setFixedWidth(120)
        searchbar.setPlaceholderText("Search ...")
        searchbar.textChanged.connect(self._update_search)
        self.searchbar = searchbar

        # create widget holder
        searchbar_action = QtWidgets.QWidgetAction(self)

        # add widget to widget holder
        searchbar_action.setDefaultWidget(self.searchbar)
        searchbar_action.setObjectName("Searchbar")

        # add update button and link function
        update_action = QtWidgets.QAction(self)
        update_action.setObjectName("Update Scripts")
        update_action.setText("Update Scripts")
        update_action.setVisible(False)
        update_action.triggered.connect(self.on_update)
        self.update_action = update_action

        # add action to menu
        self.addAction(searchbar_action)
        self.addAction(update_action)

        # add separator object
        separator = self.addSeparator()
        separator.setObjectName("separator")

    def add_menu(self, title, parent=None):
        """Create a sub menu for a parent widget

        Args:
            parent(QtWidgets.QWidget): the object to parent the menu to

            title(str): the title of the menu
        
        Returns:
             QtWidget.QMenu instance
        """

        if not parent:
            parent = self

        menu = QtWidgets.QMenu(parent, title)
        menu.setTitle(title)
        menu.setObjectName(title)
        menu.setTearOffEnabled(True)
        parent.addMenu(menu)

        return menu

    def add_script(self, parent, title, command, sourcetype, icon=None,
                   tags=None, label=None, tooltip=None):
        """Create an action item which runs a script when clicked

        Args:
            parent (QtWidget.QWidget): The widget to parent the item to

            title (str): The text which will be displayed in the menu

            command (str): The command which needs to be run when the item is
                           clicked.

            sourcetype (str): The type of command, the way the command is
                              processed is based on the source type.

            icon (str): The file path of an icon to display with the menu item

            tags (list, tuple): Keywords which describe the action

            label (str): A short description of the script which will be displayed
                         when hovering over the menu item

            tooltip (str): A tip for the user about the usage fo the tool

        Returns:
            QtWidget.QAction instance

        """

        assert tags is None or isinstance(tags, (list, tuple))
        # Ensure tags is a list
        tags = list() if tags is None else list(tags)
        tags.append(title.lower())

        assert icon is None or isinstance(icon, str), (
            "Invalid data type for icon, supported : None, string")

        # create new action
        script_action = action.Action(parent)
        script_action.setText(title)
        script_action.setObjectName(title)
        script_action.tags = tags

        # link action to root for callback library
        script_action.root = self

        # Set up the command
        script_action.sourcetype = sourcetype
        script_action.command = command

        try:
            script_action.process_command()
        except RuntimeError as e:
            raise RuntimeError("Script action can't be "
                               "processed: {}".format(e))

        if icon:
            iconfile = os.path.expandvars(icon)
            script_action.iconfile = iconfile
            script_action_icon = QtWidgets.QIcon(iconfile)
            script_action.setIcon(script_action_icon)

        if label:
            script_action.label = label

        if tooltip:
            script_action.setStatusTip(tooltip)

        script_action.triggered.connect(script_action.run_command)
        parent.addAction(script_action)

        # Add to our searchable actions
        self._script_actions.append(script_action)

        return script_action

    def build_from_configuration(self, parent, configuration):
        """Process the configurations and store the configuration

        This creates all submenus from a configuration.json file.

        When the configuration holds the key `main` all scripts under `main` will
        be added to the main menu first before adding the rest

        Args:
            parent (ScriptsMenu): script menu instance
            configuration (list): A ScriptsMenu configuration list

        Returns:
            None

        """

        for item in configuration:
            assert isinstance(item, dict), "Configuration is wrong!"

            # skip items which have no `type` key
            item_type = item.get('type', None)
            if not item_type:
                log.warning("Missing 'type' from configuration item")
                continue

            # add separator
            # Special behavior for separators
            if item_type == "separator":
                parent.addSeparator()

            # add submenu
            # items should hold a collection of submenu items (dict)
            elif item_type == "menu":
                assert "items" in item, "Menu is missing 'items' key"
                menu = self.add_menu(parent=parent, title=item["title"])
                self.build_from_configuration(menu, item["items"])

            # add script
            elif item_type == "action":
                # filter out `type` from the item dict
                config = {key: value for key, value in
                          item.items() if key != "type"}

                self.add_script(parent=parent, **config)

    def set_update_visible(self, state):
        self.update_action.setVisible(state)

    def clear_menu(self):
        """Clear all menu items which are not default

        Returns:
            None

        """

        # TODO: Set up a more robust implementation for this
        # Delete all except the first three actions
        for _action in self.actions()[3:]:
            self.removeAction(_action)

    def register_callback(self, modifiers, callback):
        self._callbacks[modifiers].append(callback)

    def _update_search(self, search):
        """Hide all the samples which do not match the user's import
        
        Returns:
            None

        """

        if not search:
            for action in self._script_actions:
                action.setVisible(True)
        else:
            for action in self._script_actions:
                action.setVisible(action.has_tag(search.lower()))

        # Set visibility for all submenus
        for action in self.actions():
            if not action.menu():
                continue

            menu = action.menu()
            visible = any(action.isVisible() for action in menu.actions())
            action.setVisible(visible)


def load_configuration(path):
    """Load the configuration from a file

    Read out the JSON file which will dictate the structure of the scripts menu

    Args:
        path (str): file path of the .JSON file

    Returns:
        dict

    """

    if not os.path.isfile(path):
        raise AttributeError("Given configuration is not "
                             "a file!\n'{}'".format(path))

    extension = os.path.splitext(path)[-1]
    if extension != ".json":
        raise AttributeError("Given configuration file has unsupported "
                             "file type, provide a .json file")

    # retrieve and store config
    with open(path, "r") as f:
        configuration = json.load(f)

    return configuration


def application(configuration, parent):
    import sys
    app = QtWidgets.QApplication(sys.argv)

    scriptsmenu = ScriptsMenu(configuration, parent)
    scriptsmenu.show()

    sys.exit(app.exec_())
