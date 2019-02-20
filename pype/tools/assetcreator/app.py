import sys

from avalon.vendor.Qt import QtWidgets, QtCore
from avalon import io, api, style
from avalon.tools import lib as parentlib
from . import widget

module = sys.modules[__name__]
module.window = None


class Window(QtWidgets.QDialog):
    """Asset creator interface

    """

    def __init__(self, parent=None):
        super(Window, self).__init__(parent)
        project_name = io.active_project()
        self.setWindowTitle("Asset creator ({0})".format(project_name))
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        # assets
        assets_widgets = QtWidgets.QWidget()
        assets_widgets.setContentsMargins(0, 0, 0, 0)
        assets_layout = QtWidgets.QVBoxLayout(assets_widgets)
        assets = widget.AssetWidget()
        assets.view.setSelectionMode(assets.view.ExtendedSelection)
        assets_layout.addWidget(assets)

        # info
        label_name = QtWidgets.QLabel("Name:")
        input_name = QtWidgets.QLineEdit()
        input_name.setPlaceholderText("<asset name>")

        # Parent
        label_parent = QtWidgets.QLabel("Parent:")
        input_parent = QtWidgets.QLineEdit()
        input_parent.setReadOnly(True)
        input_parent.setStyleSheet("background-color: #333333;")  # greyed out

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(label_name)
        layout.addWidget(input_name)
        layout.addWidget(label_parent)
        layout.addWidget(input_parent)

        body = QtWidgets.QSplitter()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Expanding)
        body.setOrientation(QtCore.Qt.Horizontal)
        body.addWidget(assets_widgets)
        body.addWidget(layout)
        body.setStretchFactor(0, 100)
        body.setStretchFactor(1, 65)

        # statusbar
        message = QtWidgets.QLabel()
        message.setFixedHeight(20)

        statusbar = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(statusbar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(message)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(body)
        layout.addWidget(statusbar)

        self.data = {
            "label": {
                "message": message,
            },
            "model": {
                "assets": assets
            },
            "buttons": {

            }
        }

        # signals
        assets.selection_changed.connect(self.on_asset_changed)
        assets.silo_changed.connect(self.on_silo_changed)

        self.resize(800, 500)

        self.echo("Connected to project: {0}".format(project_name))

    def refresh(self):
        self.data["model"]["assets"].refresh()
        # set silo on start so tasks for silo are shown
        current_silo = self.data["model"]["assets"].get_current_silo()
        if current_silo != "":
            self.on_asset_changed()

    def echo(self, message):
        widget = self.data["label"]["message"]
        widget.setText(str(message))

        QtCore.QTimer.singleShot(5000, lambda: widget.setText(""))

        print(message)

    def on_add_asset(self):
        """Show add asset dialog"""

        # Get parent asset (active index in selection)
        model = self.data["model"]["assets"]
        parent_id = model.get_active_asset()

        # Get active silo
        silo = model.get_current_silo()
        if not silo:
            QtWidgets.QMessageBox.critical(self, "Missing silo",
                                           "Please create a silo first.\n"
                                           "Use the + tab at the top left.")
            return

        def _on_current_asset_changed():
            """Callback on current asset changed in item widget.

            Whenever the current index changes in the item widget we want to
            update under which asset we're creating *to be created* asset.

            """

            parent = model.get_active_asset()

        # Signals
        model.current_changed.connect(_on_current_asset_changed)

    def on_asset_changed(self):
        """Callback on asset selection changed

        This updates the task view.

        """

        model = self.data["model"]["assets"]
        selected = model.get_selected_assets()
        # Show task of silo if nothing selected
        if len(selected) < 1:
            silo = model.get_silo_object()
            if silo:
                selected = [silo['_id']]
        self.data['model']['tasks'].set_assets(selected)

    def on_silo_changed(self, silo):
        """Callback on asset silo changed"""
        if silo:
            self.echo("Silo changed to: {0}".format(silo))


def show(root=None, debug=False, parent=None):
    """Display Loader GUI

    Arguments:
        debug (bool, optional): Run loader in debug-mode,
            defaults to False

    """

    try:
        module.window.close()
        del module.window
    except (RuntimeError, AttributeError):
        pass

    if debug is True:
        io.install()

    with parentlib.application():
        window = Window(parent)
        window.setStyleSheet(style.load_stylesheet())
        window.show()
        window.refresh()

        module.window = window


def cli(args):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("project")

    args = parser.parse_args(args)
    project = args.project

    io.install()

    api.Session["AVALON_PROJECT"] = project

    show()
