import re
from avalon import api
from pype.hosts import resolve
from avalon.vendor import qargparse
from pype.api import config

from Qt import QtWidgets, QtCore


class CreatorWidget(QtWidgets.QDialog):

    # output items
    items = dict()

    def __init__(self, name, info, presets, parent=None):
        super(CreatorWidget, self).__init__(parent)

        self.setObjectName(name)

        self.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.CustomizeWindowHint
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowCloseButtonHint
            | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setWindowTitle(name or "Pype Creator Input")

        # Where inputs and labels are set
        self.content_widget = [QtWidgets.QWidget(self)]
        top_layout = QtWidgets.QFormLayout(self.content_widget[0])
        top_layout.setObjectName("ContentLayout")
        top_layout.addWidget(Spacer(5, self))

        # first add widget tag line
        top_layout.addWidget(QtWidgets.QLabel(info))

        top_layout.addWidget(Spacer(5, self))

        # main dynamic layout
        self.content_widget.append(QtWidgets.QWidget(self))
        content_layout = QtWidgets.QFormLayout(self.content_widget[-1])

        # add preset data into input widget layout
        self.items = self.add_presets_to_layout(content_layout, presets)

        # Confirmation buttons
        btns_widget = QtWidgets.QWidget(self)
        btns_layout = QtWidgets.QHBoxLayout(btns_widget)

        cancel_btn = QtWidgets.QPushButton("Cancel")
        btns_layout.addWidget(cancel_btn)

        ok_btn = QtWidgets.QPushButton("Ok")
        btns_layout.addWidget(ok_btn)

        # Main layout of the dialog
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(0)

        # adding content widget
        for w in self.content_widget:
            main_layout.addWidget(w)

        main_layout.addWidget(btns_widget)

        ok_btn.clicked.connect(self._on_ok_clicked)
        cancel_btn.clicked.connect(self._on_cancel_clicked)

        stylesheet = resolve.menu.load_stylesheet()
        self.setStyleSheet(stylesheet)

    def _on_ok_clicked(self):
        self.result = self.value(self.items)
        self.close()

    def _on_cancel_clicked(self):
        self.result = None
        self.close()

    def value(self, data):
        for k, v in data.items():
            if isinstance(v, dict):
                print(f"nested: {k}")
                data[k] = self.value(v)
            elif getattr(v, "value", None):
                print(f"normal int: {k}")
                result = v.value()
                data[k] = result()
            else:
                print(f"normal text: {k}")
                result = v.text()
                data[k] = result()
        return data

    def camel_case_split(self, text):
        matches = re.finditer(
            '.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', text)
        return " ".join([str(m.group(0)).capitalize() for m in matches])

    def create_row(self, layout, type, text, **kwargs):
        # get type attribute from qwidgets
        attr = getattr(QtWidgets, type)

        # convert label text to normal capitalized text with spaces
        label_text = self.camel_case_split(text)

        # assign the new text to lable widget
        label = QtWidgets.QLabel(label_text)
        label.setObjectName("LineLabel")

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

        # add to layout
        layout.addRow(label, item)

        return item

    def add_presets_to_layout(self, content_layout, data):
        for k, v in data.items():
            if isinstance(v, dict):
                # adding spacer between sections
                self.content_widget.append(QtWidgets.QWidget(self))
                devider = QtWidgets.QVBoxLayout(self.content_widget[-1])
                devider.addWidget(Spacer(5, self))
                devider.setObjectName("Devider")

                # adding nested layout with label
                self.content_widget.append(QtWidgets.QWidget(self))
                nested_content_layout = QtWidgets.QFormLayout(
                    self.content_widget[-1])
                nested_content_layout.setObjectName("NestedContentLayout")

                # add nested key as label
                self.create_row(nested_content_layout, "QLabel", k)
                data[k] = self.add_presets_to_layout(nested_content_layout, v)
            elif isinstance(v, str):
                print(f"layout.str: {k}")
                print(f"content_layout: {content_layout}")
                data[k] = self.create_row(
                    content_layout, "QLineEdit", k, setText=v)
            elif isinstance(v, int):
                print(f"layout.int: {k}")
                print(f"content_layout: {content_layout}")
                data[k] = self.create_row(
                    content_layout, "QSpinBox", k, setValue=v)
        return data


class Spacer(QtWidgets.QWidget):
    def __init__(self, height, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        self.setFixedHeight(height)

        real_spacer = QtWidgets.QWidget(self)
        real_spacer.setObjectName("Spacer")
        real_spacer.setFixedHeight(height)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(real_spacer)

        self.setLayout(layout)


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

        self.widget = CreatorWidget
