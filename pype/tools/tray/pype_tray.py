import os
import sys
import platform
from avalon import style
from Qt import QtCore, QtGui, QtWidgets, QtSvg
from pype.resources import get_resource
from pype.api import config, Logger


class TrayManager:
    """Cares about context of application.

    Load submenus, actions, separators and modules into tray's context.
    """
    modules = {}
    services = {}
    services_submenu = None

    errors = []
    items = (
        config.get_presets(first_run=True)
        .get('tray', {})
        .get('menu_items', [])
    )
    available_sourcetypes = ['python', 'file']

    def __init__(self, tray_widget, main_window):
        self.tray_widget = tray_widget
        self.main_window = main_window
        self.log = Logger().get_logger(self.__class__.__name__)

        self.icon_run = QtGui.QIcon(get_resource('circle_green.png'))
        self.icon_stay = QtGui.QIcon(get_resource('circle_orange.png'))
        self.icon_failed = QtGui.QIcon(get_resource('circle_red.png'))

        self.services_thread = None

    def process_presets(self):
        """Add modules to tray by presets.

        This is start up method for TrayManager. Loads presets and import
        modules described in "menu_items.json". In `item_usage` key you can
        specify by item's title or import path if you want to import it.
        Example of "menu_items.json" file:
            {
                "item_usage": {
                    "Statics Server": false
                }
            }, {
                "item_import": [{
                    "title": "Ftrack",
                    "type": "module",
                    "import_path": "pype.ftrack.tray",
                    "fromlist": ["pype", "ftrack"]
                }, {
                    "title": "Statics Server",
                    "type": "module",
                    "import_path": "pype.services.statics_server",
                    "fromlist": ["pype","services"]
                }]
            }
        In this case `Statics Server` won't be used.
        """
        # Backwards compatible presets loading
        if isinstance(self.items, list):
            items = self.items
        else:
            items = []
            # Get booleans is module should be used
            usages = self.items.get("item_usage") or {}
            for item in self.items.get("item_import", []):
                import_path = item.get("import_path")
                title = item.get("title")

                item_usage = usages.get(title)
                if item_usage is None:
                    item_usage = usages.get(import_path, True)

                if item_usage:
                    items.append(item)
                else:
                    if not title:
                        title = import_path
                    self.log.debug("{} - Module ignored".format(title))

        if items:
            self.process_items(items, self.tray_widget.menu)

        # Add services if they are
        if self.services_submenu is not None:
            self.tray_widget.menu.addMenu(self.services_submenu)

        # Add separator
        if items and self.services_submenu is not None:
            self.add_separator(self.tray_widget.menu)

        # Add Exit action to menu
        aExit = QtWidgets.QAction("&Exit", self.tray_widget)
        aExit.triggered.connect(self.tray_widget.exit)
        self.tray_widget.menu.addAction(aExit)

        # Tell each module which modules were imported
        self.connect_modules()
        self.start_modules()

    def process_items(self, items, parent_menu):
        """ Loop through items and add them to parent_menu.

        :param items: contains dictionary objects representing each item
        :type items: list
        :param parent_menu: menu where items will be add
        :type parent_menu: QtWidgets.QMenu
        """
        for item in items:
            i_type = item.get('type', None)
            result = False
            if i_type is None:
                continue
            elif i_type == 'module':
                result = self.add_module(item, parent_menu)
            elif i_type == 'action':
                result = self.add_action(item, parent_menu)
            elif i_type == 'menu':
                result = self.add_menu(item, parent_menu)
            elif i_type == 'separator':
                result = self.add_separator(parent_menu)

            if result is False:
                self.errors.append(item)

    def add_module(self, item, parent_menu):
        """Inicialize object of module and add it to context.

        :param item: item from presets containing information about module
        :type item: dict
        :param parent_menu: menu where module's submenus/actions will be add
        :type parent_menu: QtWidgets.QMenu
        :returns: success of module implementation
        :rtype: bool

        REQUIRED KEYS (item):
            :import_path (*str*):
                - full import path as python's import
                - e.g. *"path.to.module"*
            :fromlist (*list*):
                - subparts of import_path (as from is used)
                - e.g. *["path", "to"]*
        OPTIONAL KEYS (item):
            :title (*str*):
                - represents label shown in services menu
                - import_path is used if title is not set
                - title is not used at all if module is not a service

        .. note::
            Module is added as **service** if object does not have
            *tray_menu* method.
        """
        import_path = item.get('import_path', None)
        title = item.get('title', import_path)
        fromlist = item.get('fromlist', [])
        try:
            module = __import__(
                "{}".format(import_path),
                fromlist=fromlist
            )
            obj = module.tray_init(self.tray_widget, self.main_window)
            name = obj.__class__.__name__
            if hasattr(obj, 'tray_menu'):
                obj.tray_menu(parent_menu)
            else:
                if self.services_submenu is None:
                    self.services_submenu = QtWidgets.QMenu(
                        'Services', self.tray_widget.menu
                    )
                action = QtWidgets.QAction(title, self.services_submenu)
                action.setIcon(self.icon_run)
                self.services_submenu.addAction(action)
                if hasattr(obj, 'set_qaction'):
                    obj.set_qaction(action, self.icon_failed)
            self.modules[name] = obj
            self.log.info("{} - Module imported".format(title))
        except ImportError as ie:
            if self.services_submenu is None:
                self.services_submenu = QtWidgets.QMenu(
                    'Services', self.tray_widget.menu
                )
            action = QtWidgets.QAction(title, self.services_submenu)
            action.setIcon(self.icon_failed)
            self.services_submenu.addAction(action)
            self.log.warning(
                "{} - Module import Error: {}".format(title, str(ie)),
                exc_info=True
            )
            return False
        return True

    def add_action(self, item, parent_menu):
        """Adds action to parent_menu.

        :param item: item from presets containing information about action
        :type item: dictionary
        :param parent_menu: menu where action will be added
        :type parent_menu: QtWidgets.QMenu
        :returns: success of adding item to parent_menu
        :rtype: bool

        REQUIRED KEYS (item):
            :title (*str*):
                - represents label shown in menu
            :sourcetype (*str*):
                - type of action *enum["file", "python"]*
            :command (*str*):
                - filepath to script *(sourcetype=="file")*
                - python code as string *(sourcetype=="python")*
        OPTIONAL KEYS (item):
            :tooltip (*str*):
                - will be shown when hover over action
        """
        sourcetype = item.get('sourcetype', None)
        command = item.get('command', None)
        title = item.get('title', '*ERROR*')
        tooltip = item.get('tooltip', None)

        if sourcetype not in self.available_sourcetypes:
            self.log.error('item "{}" has invalid sourcetype'.format(title))
            return False
        if command is None or command.strip() == '':
            self.log.error('item "{}" has invalid command'.format(title))
            return False

        new_action = QtWidgets.QAction(title, parent_menu)
        if tooltip is not None and tooltip.strip() != '':
            new_action.setToolTip(tooltip)

        if sourcetype == 'python':
            new_action.triggered.connect(
                lambda: exec(command)
            )
        elif sourcetype == 'file':
            command = os.path.normpath(command)
            if '$' in command:
                command_items = command.split(os.path.sep)
                for i in range(len(command_items)):
                    if command_items[i].startswith('$'):
                        # TODO: raise error if environment was not found?
                        command_items[i] = os.environ.get(
                            command_items[i].replace('$', ''), command_items[i]
                        )
                command = os.path.sep.join(command_items)

            new_action.triggered.connect(
                lambda: exec(open(command).read(), globals())
            )

        parent_menu.addAction(new_action)

    def add_menu(self, item, parent_menu):
        """ Adds submenu to parent_menu.

        :param item: item from presets containing information about menu
        :type item: dictionary
        :param parent_menu: menu where submenu will be added
        :type parent_menu: QtWidgets.QMenu
        :returns: success of adding item to parent_menu
        :rtype: bool

        REQUIRED KEYS (item):
            :title (*str*):
                - represents label shown in menu
            :items (*list*):
                - list of submenus / actions / separators / modules *(dict)*
        """
        try:
            title = item.get('title', None)
            if title is None or title.strip() == '':
                self.log.error('Missing title in menu from presets')
                return False
            new_menu = QtWidgets.QMenu(title, parent_menu)
            new_menu.setProperty('submenu', 'on')
            parent_menu.addMenu(new_menu)

            self.process_items(item.get('items', []), new_menu)
            return True
        except Exception:
            return False

    def add_separator(self, parent_menu):
        """ Adds separator to parent_menu.

        :param parent_menu: menu where submenu will be added
        :type parent_menu: QtWidgets.QMenu
        :returns: success of adding item to parent_menu
        :rtype: bool
        """
        try:
            parent_menu.addSeparator()
            return True
        except Exception:
            return False

    def connect_modules(self):
        """Sends all imported modules to imported modules
        which have process_modules method.
        """
        for obj in self.modules.values():
            if hasattr(obj, 'process_modules'):
                obj.process_modules(self.modules)

    def start_modules(self):
        """Modules which can be modified by another modules and
        must be launched after *connect_modules* should have tray_start
        to start their process afterwards. (e.g. Ftrack actions)
        """
        for obj in self.modules.values():
            if hasattr(obj, 'tray_start'):
                obj.tray_start()

    def on_exit(self):
        for obj in self.modules.values():
            if hasattr(obj, 'tray_exit'):
                try:
                    obj.tray_exit()
                except Exception:
                    self.log.error("Failed to exit module {}".format(
                        obj.__class__.__name__
                    ))


class SystemTrayIcon(QtWidgets.QSystemTrayIcon):
    """Tray widget.

    :param parent: Main widget that cares about all GUIs
    :type parent: QtWidgets.QMainWindow
    """
    def __init__(self, parent):
        if os.getenv("PYPE_DEV"):
            icon_file_name = "icon_dev.png"
        else:
            icon_file_name = "icon.png"

        self.icon = QtGui.QIcon(get_resource(icon_file_name))

        QtWidgets.QSystemTrayIcon.__init__(self, self.icon, parent)

        # Store parent - QtWidgets.QMainWindow()
        self.parent = parent

        # Setup menu in Tray
        self.menu = QtWidgets.QMenu()
        self.menu.setStyleSheet(style.load_stylesheet())

        # Set modules
        self.tray_man = TrayManager(self, self.parent)
        self.tray_man.process_presets()

        # Catch activate event
        self.activated.connect(self.on_systray_activated)
        # Add menu to Context of SystemTrayIcon
        self.setContextMenu(self.menu)

    def on_systray_activated(self, reason):
        # show contextMenu if left click
        if platform.system().lower() == "darwin":
            return
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            position = QtGui.QCursor().pos()
            self.contextMenu().popup(position)

    def exit(self):
        """ Exit whole application.

        - Icon won't stay in tray after exit.
        """
        self.hide()
        self.tray_man.on_exit()
        QtCore.QCoreApplication.exit()


class TrayMainWindow(QtWidgets.QMainWindow):
    """ TrayMainWindow is base of Pype application.

    Every widget should have set this window as parent because
    QSystemTrayIcon widget is not allowed to be a parent of any widget.

    :param app: Qt application manages application's control flow
    :type app: QtWidgets.QApplication

    .. note::
        *TrayMainWindow* has ability to show **working** widget.
        Calling methods:
        - ``show_working()``
        - ``hide_working()``
    .. todo:: Hide working widget if idle is too long
    """
    def __init__(self, app):
        super().__init__()
        self.app = app

        self.set_working_widget()

        self.trayIcon = SystemTrayIcon(self)
        self.trayIcon.show()

    def set_working_widget(self):
        image_file = get_resource('working.svg')
        img_pix = QtGui.QPixmap(image_file)
        if image_file.endswith('.svg'):
            widget = QtSvg.QSvgWidget(image_file)
        else:
            widget = QtWidgets.QLabel()
            widget.setPixmap(img_pix)

        # Set widget properties
        widget.setGeometry(img_pix.rect())
        widget.setMask(img_pix.mask())
        widget.setWindowFlags(
            QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.FramelessWindowHint
        )
        widget.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        self.center_widget(widget)
        self._working_widget = widget
        self.helper = DragAndDropHelper(self._working_widget)

    def center_widget(self, widget):
        frame_geo = widget.frameGeometry()
        screen = self.app.desktop().cursor().pos()
        center_point = self.app.desktop().screenGeometry(
            self.app.desktop().screenNumber(screen)
        ).center()
        frame_geo.moveCenter(center_point)
        widget.move(frame_geo.topLeft())

    def show_working(self):
        self._working_widget.show()

    def hide_working(self):
        self.center_widget(self._working_widget)
        self._working_widget.hide()


class DragAndDropHelper:
    """ Helper adds to widget drag and drop ability

    :param widget: Qt Widget where drag and drop ability will be added
    """
    def __init__(self, widget):
        self.widget = widget
        self.widget.mousePressEvent = self.mousePressEvent
        self.widget.mouseMoveEvent = self.mouseMoveEvent
        self.widget.mouseReleaseEvent = self.mouseReleaseEvent

    def mousePressEvent(self, event):
        self.__mousePressPos = None
        self.__mouseMovePos = None
        if event.button() == QtCore.Qt.LeftButton:
            self.__mousePressPos = event.globalPos()
            self.__mouseMovePos = event.globalPos()

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            # adjust offset from clicked point to origin of widget
            currPos = self.widget.mapToGlobal(
                self.widget.pos()
            )
            globalPos = event.globalPos()
            diff = globalPos - self.__mouseMovePos
            newPos = self.widget.mapFromGlobal(currPos + diff)
            self.widget.move(newPos)
            self.__mouseMovePos = globalPos

    def mouseReleaseEvent(self, event):
        if self.__mousePressPos is not None:
            moved = event.globalPos() - self.__mousePressPos
            if moved.manhattanLength() > 3:
                event.ignore()
                return


class PypeTrayApplication(QtWidgets.QApplication):
    """Qt application manages application's control flow."""
    def __init__(self):
        super(self.__class__, self).__init__(sys.argv)
        # Allows to close widgets without exiting app
        self.setQuitOnLastWindowClosed(False)
        # Sets up splash
        splash_widget = self.set_splash()

        splash_widget.show()
        self.processEvents()
        self.main_window = TrayMainWindow(self)
        splash_widget.hide()

    def set_splash(self):
        if os.getenv("PYPE_DEV"):
            splash_file_name = "splash_dev.png"
        else:
            splash_file_name = "splash.png"
        splash_pix = QtGui.QPixmap(get_resource(splash_file_name))
        splash = QtWidgets.QSplashScreen(splash_pix)
        splash.setMask(splash_pix.mask())
        splash.setEnabled(False)
        splash.setWindowFlags(
            QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.FramelessWindowHint
        )
        return splash
