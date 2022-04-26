import os
import sys
import ctypes
import signal

from bson.objectid import ObjectId
from Qt import QtWidgets, QtCore, QtGui

from .widgets import (
    AssetWidget, FamilyWidget, ComponentsWidget, ShadowWidget
)
from .widgets.constants import HOST_NAME
from openpype import style
from openpype.api import resources
from openpype.pipeline import AvalonMongoDB
from openpype.modules import ModulesManager


class Window(QtWidgets.QDialog):
    """Main window of Standalone publisher.

    :param parent: Main widget that cares about all GUIs
    :type parent: QtWidgets.QMainWindow
    """
    _jobs = {}
    valid_family = False
    valid_components = False
    initialized = False
    WIDTH = 1100
    HEIGHT = 500

    def __init__(self, pyblish_paths, parent=None):
        super(Window, self).__init__(parent=parent)
        self._db = AvalonMongoDB()
        self._db.install()

        try:
            settings = QtCore.QSettings("pypeclub", "StandalonePublisher")
        except Exception:
            settings = None

        self._settings = settings

        self.pyblish_paths = pyblish_paths

        self.setWindowTitle("Standalone Publish")
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        # Validators
        self.valid_parent = False

        # assets widget
        widget_assets = AssetWidget(self._db, settings, self)

        # family widget
        widget_family = FamilyWidget(dbcon=self._db, parent=self)

        # components widget
        widget_components = ComponentsWidget(parent=self)

        # Body
        body = QtWidgets.QSplitter()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )
        body.setOrientation(QtCore.Qt.Horizontal)
        body.addWidget(widget_assets)
        body.addWidget(widget_family)
        body.addWidget(widget_components)
        body.setStretchFactor(body.indexOf(widget_assets), 2)
        body.setStretchFactor(body.indexOf(widget_family), 3)
        body.setStretchFactor(body.indexOf(widget_components), 5)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(body)

        self.resize(self.WIDTH, self.HEIGHT)

        # signals
        widget_assets.selection_changed.connect(self.on_asset_changed)
        widget_assets.task_changed.connect(self._on_task_change)
        widget_assets.project_changed.connect(self.on_project_change)
        widget_family.stateChanged.connect(self.set_valid_family)

        self.widget_assets = widget_assets
        self.widget_family = widget_family
        self.widget_components = widget_components

        # on start
        self.on_start()

    @property
    def db(self):
        ''' Returns DB object for MongoDB I/O
        '''
        return self._db

    def on_start(self):
        ''' Things must be done when initialized.
        '''
        # Refresh asset input in Family widget
        self.on_asset_changed()
        self.widget_components.validation()
        # Initializing shadow widget
        self.shadow_widget = ShadowWidget(self)
        self.shadow_widget.setVisible(False)

    def resizeEvent(self, event=None):
        ''' Helps resize shadow widget
        '''
        position_x = (
            self.frameGeometry().width()
            - self.shadow_widget.frameGeometry().width()
        ) / 2
        position_y = (
            self.frameGeometry().height()
            - self.shadow_widget.frameGeometry().height()
        ) / 2
        self.shadow_widget.move(position_x, position_y)
        w = self.frameGeometry().width()
        h = self.frameGeometry().height()
        self.shadow_widget.resize(QtCore.QSize(w, h))
        if event:
            super().resizeEvent(event)

    def get_avalon_parent(self, entity):
        ''' Avalon DB entities helper - get all parents (exclude project).
        '''
        parent_id = entity['data']['visualParent']
        parents = []
        if parent_id is not None:
            parent = self.db.find_one({'_id': parent_id})
            parents.extend(self.get_avalon_parent(parent))
            parents.append(parent['name'])
        return parents

    def on_project_change(self, project_name):
        self.widget_family.refresh()

    def on_asset_changed(self):
        '''Callback on asset selection changed

        Updates the task view.

        '''
        selected = [
            asset_id for asset_id in self.widget_assets.get_selected_assets()
            if isinstance(asset_id, ObjectId)
        ]
        if len(selected) == 1:
            self.valid_parent = True
            asset = self.db.find_one({"_id": selected[0], "type": "asset"})
            self.widget_family.change_asset(asset['name'])
        else:
            self.valid_parent = False
            self.widget_family.change_asset(None)
        self.widget_family.on_data_changed()

    def _on_task_change(self):
        self.widget_family.on_task_change()

    def keyPressEvent(self, event):
        ''' Handling Ctrl+V KeyPress event
        Can handle:
            - files/folders in clipboard (tested only on Windows OS)
            - copied path of file/folder in clipboard ('c:/path/to/folder')
        '''
        if (
            event.key() == QtCore.Qt.Key_V
            and event.modifiers() == QtCore.Qt.ControlModifier
        ):
            clip = QtWidgets.QApplication.clipboard()
            self.widget_components.process_mime_data(clip)
        super().keyPressEvent(event)

    def working_start(self, msg=None):
        ''' Shows shadowed foreground with message
        :param msg: Message that will be displayed
        (set to `Please wait...` if `None` entered)
        :type msg: str
        '''
        if msg is None:
            msg = 'Please wait...'
        self.shadow_widget.message = msg
        self.shadow_widget.setVisible(True)
        self.resizeEvent()
        QtWidgets.QApplication.processEvents()

    def working_stop(self):
        ''' Hides shadowed foreground
        '''
        if self.shadow_widget.isVisible():
            self.shadow_widget.setVisible(False)
        # Refresh version
        self.widget_family.on_version_refresh()

    def set_valid_family(self, valid):
        ''' Sets `valid_family` attribute for validation

        .. note::
            if set to `False` publishing is not possible
        '''
        self.valid_family = valid
        # If widget_components not initialized yet
        if hasattr(self, 'widget_components'):
            self.widget_components.validation()

    def collect_data(self):
        ''' Collecting necessary data for pyblish from child widgets
        '''
        data = {}
        data.update(self.widget_assets.collect_data())
        data.update(self.widget_family.collect_data())
        data.update(self.widget_components.collect_data())

        return data


def main():
    os.environ["AVALON_APP"] = HOST_NAME

    # Allow to change icon of running process in windows taskbar
    if os.name == "nt":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            u"standalonepublish"
        )

    qt_app = QtWidgets.QApplication([])
    # app.setQuitOnLastWindowClosed(False)
    qt_app.setStyleSheet(style.load_stylesheet())
    icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
    qt_app.setWindowIcon(icon)

    def signal_handler(sig, frame):
        print("You pressed Ctrl+C. Process ended.")
        qt_app.quit()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    modules_manager = ModulesManager()
    module = modules_manager.modules_by_name["standalonepublish_tool"]

    window = Window(module.publish_paths)
    window.show()

    sys.exit(qt_app.exec_())
