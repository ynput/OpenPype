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

        # Validators
        self.valid_parent = False

        # assets
        assets_widgets = QtWidgets.QWidget()
        assets_widgets.setContentsMargins(0, 0, 0, 0)
        assets_layout = QtWidgets.QVBoxLayout(assets_widgets)
        assets = widget.AssetWidget()
        assets.view.setSelectionMode(assets.view.ExtendedSelection)
        assets_layout.addWidget(assets)

        # info
        widget_name = QtWidgets.QWidget()
        widget_name.setContentsMargins(0, 0, 0, 0)
        layout_name = QtWidgets.QHBoxLayout(widget_name)
        label_name = QtWidgets.QLabel("Name:")
        input_name = QtWidgets.QLineEdit()
        input_name.setPlaceholderText("<asset name>")
        layout_name.addWidget(label_name)
        layout_name.addWidget(input_name)

        # Parent
        widget_parent = QtWidgets.QWidget()
        widget_parent.setContentsMargins(0, 0, 0, 0)
        layout_parent = QtWidgets.QHBoxLayout(widget_parent)
        label_parent = QtWidgets.QLabel("Parent:")
        input_parent = QtWidgets.QLineEdit()
        input_parent.setReadOnly(True)
        input_parent.setStyleSheet("background-color: #333333;")  # greyed out
        layout_parent.addWidget(label_parent)
        layout_parent.addWidget(input_parent)

        info_widget = QtWidgets.QWidget()
        info_widget.setContentsMargins(0, 0, 0, 0)
        info_layout = QtWidgets.QVBoxLayout(info_widget)
        info_layout.addWidget(widget_parent)
        info_layout.addWidget(widget_name)

        body = QtWidgets.QSplitter()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Expanding)
        body.setOrientation(QtCore.Qt.Horizontal)
        body.addWidget(assets_widgets)
        body.addWidget(info_widget)
        body.setStretchFactor(0, 100)
        body.setStretchFactor(1, 200)

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
            "inputs": {
                "parent": input_parent,
                "name": input_name
            },
            "buttons": {

            }
        }

        # signals
        assets.selection_changed.connect(self.on_asset_changed)
        # on start
        self.on_asset_changed()
        self.resize(800, 500)

        self.echo("Connected to project: {0}".format(project_name))

    def refresh(self):
        self.data["model"]["assets"].refresh()

    def echo(self, message):
        widget = self.data["label"]["message"]
        widget.setText(str(message))

        QtCore.QTimer.singleShot(5000, lambda: widget.setText(""))

        print(message)

    def on_asset_changed(self):
        """Callback on asset selection changed

        This updates the task view.

        """
        assets_model = self.data["model"]["assets"]
        parent_input = self.data['inputs']['parent']
        selected = assets_model.get_selected_assets()
        if len(selected) > 1:
            self.valid_parent = False
            parent_input.setText('< Please select only one asset! >')
        elif len(selected) == 1:
            self.valid_parent = True
            asset = io.find_one({"_id": selected[0], "type": "asset"})
            parent_input.setText(asset['name'])
        else:
            self.valid_parent = False
            parent_input.setText('< Nothing is selected >')


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
