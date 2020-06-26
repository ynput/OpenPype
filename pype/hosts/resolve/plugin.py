import sys
import re
from avalon import api
from pype.hosts import resolve
from avalon.vendor import qargparse
from pype.api import config

from Qt import QtWidgets, QtCore


class Universal_widget(QtWidgets.QDialog):

    # output items
    items = dict()

    def __init__(self, name, presets, parent=None):
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
        self.content_layout = QtWidgets.QFormLayout(content_widget)
        self.content_layout.setObjectName("ContentLayout")

        # first add widget tag line
        self.create_row("QLabel", name)

        # add preset data into input widget layout
        self.add_presets_to_layout(presets)

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

    def camel_case_split(self, text):
        matches = re.finditer(
            '.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', text)
        return " ".join([str(m.group(0)).capitalize() for m in matches])

    def create_row(self, type, text, **kwargs):
        # get type attribute from qwidgets
        attr = getattr(QtWidgets, type)

        # convert label text to normal capitalized text with spaces
        label_text = self.camel_case_split(text)

        # assign the new text to lable widget
        label = QtWidgets.QLabel(label_text)

        # create attribute name text strip of spaces
        attr_name = text.replace(" ", "")

        # create attribute and assign default values
        setattr(
            self,
            attr_name,
            attr(parent=self))

        # assign the created attribute to variable
        item = getattr(self, attr_name)
        for func, val in kwargs.items():
            if getattr(item, func):
                func_attr = getattr(item, func)
                func_attr(val)

        self.content_layout.addRow(label, item)
        return item

    def add_presets_to_layout(self, data):
        for k, v in data.items():
            if isinstance(v, dict):
                # if nested dict then create label
                # TODO: create also new layout
                self.create_row("QLabel", k)
                self.add_presets_to_layout(v)
            elif isinstance(v, str):
                item = self.create_row("QLineEdit", k, setText=v)
            elif isinstance(v, int):
                item = self.create_row("QSpinBox", k, setValue=v)

            # add it to items for later requests
            self.items.update({
                k: item
            })


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
