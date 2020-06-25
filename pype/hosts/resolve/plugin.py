import sys
from avalon import api
from pype.hosts import resolve
from avalon.vendor import qargparse
from pype.api import config

from Qt import QtWidgets, QtCore


class Universal_widget(QtWidgets.QDialog):
    def __init__(self, widgets, parent=None):
        super(Universal_widget, self).__init__(parent)

        self.setObjectName("PypeCreatorInput")

        self.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.CustomizeWindowHint
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowCloseButtonHint
            | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setWindowTitle("CreatorInput")

        # Where inputs and labels are set
        content_widget = QtWidgets.QWidget(self)
        content_layout = QtWidgets.QFormLayout(content_widget)

        self.items = dict()
        for w in widgets:
            attr = getattr(QtWidgets, w["type"])
            label = QtWidgets.QLabel(w["label"])
            attr_name = w["label"].replace(" ", "").lower()
            setattr(
                self,
                attr_name,
                attr(parent=self))
            item = getattr(self, attr_name)
            func = next((k for k in w if k not in ["label", "type"]), None)
            if func:
                if getattr(item, func):
                    func_attr = getattr(item, func)
                    func_attr(w[func])

            content_layout.addRow(label, item)
            self.items.update({
                w["label"]: item
            })

        # Confirmation buttons
        btns_widget = QtWidgets.QWidget(self)
        btns_layout = QtWidgets.QHBoxLayout(btns_widget)

        cancel_btn = QtWidgets.QPushButton("Cancel")
        btns_layout.addWidget(cancel_btn)

        ok_btn = QtWidgets.QPushButton("Ok")
        btns_layout.addWidget(ok_btn)

        # Main layout of the dialog
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 20, 10, 20)
        main_layout.setSpacing(0)

        main_layout.addWidget(content_widget)
        main_layout.addWidget(btns_widget)

        ok_btn.clicked.connect(self._on_ok_clicked)
        cancel_btn.clicked.connect(self._on_cancel_clicked)

        stylesheet = resolve.menu.load_stylesheet()
        self.setStyleSheet(stylesheet)

    def _on_ok_clicked(self):
        self.value()
        self.close()

    def _on_cancel_clicked(self):
        self.result = None
        self.close()

    def value(self):
        for k, v in self.items.items():
            if getattr(v, "value", None):
                result = getattr(v, "value")
            else:
                result = getattr(v, "text")
            self.items[k] = result()
        self.result = self.items


def get_reference_node_parents(ref):
    """Return all parent reference nodes of reference node

    Args:
        ref (str): reference node.

    Returns:
        list: The upstream parent reference nodes.

    """
    parents = []
    return parents


class SequenceLoader(api.Loader):
    """A basic SequenceLoader for Resolve

    This will implement the basic behavior for a loader to inherit from that
    will containerize the reference and will implement the `remove` and
    `update` logic.

    """

    options = [
        qargparse.Toggle(
            "handles",
            label="Include handles",
            default=0,
            help="Load with handles or without?"
        ),
        qargparse.Choice(
            "load_to",
            label="Where to load clips",
            items=[
                "Current timeline",
                "New timeline"
            ],
            default=0,
            help="Where do you want clips to be loaded?"
        ),
        qargparse.Choice(
            "load_how",
            label="How to load clips",
            items=[
                "original timing",
                "sequential in order"
            ],
            default=0,
            help="Would you like to place it at orignal timing?"
        )
    ]

    def load(
        self,
        context,
        name=None,
        namespace=None,
        options=None
    ):
        pass

    def update(self, container, representation):
        """Update an existing `container`
        """
        pass

    def remove(self, container):
        """Remove an existing `container`
        """
        pass


class Creator(api.Creator):
    """Creator class wrapper
    """
    marker_color = "Purple"

    def __init__(self, *args, **kwargs):
        super(Creator, self).__init__(*args, **kwargs)
        self.presets = config.get_presets()['plugins']["resolve"][
            "create"].get(self.__class__.__name__, {})

        # adding basic current context resolve objects
        self.project = resolve.get_current_project()
        self.sequence = resolve.get_current_sequence()

        if (self.options or {}).get("useSelection"):
            self.selected = resolve.get_current_track_items(filter=True)
        else:
            self.selected = resolve.get_current_track_items(filter=False)

        self.widget = Universal_widget
