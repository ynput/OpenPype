"""
NOTE: The required `Qt` module has changed to use the one that vendorized.
      Remember to change to relative import when updating this.
"""

import re
import logging

from collections import OrderedDict as odict
from Qt import QtCore, QtWidgets, QtGui
import qtawesome

__version__ = "0.5.2"
_log = logging.getLogger(__name__)
_type = type  # used as argument

try:
    # Python 2
    _basestring = basestring
except NameError:
    _basestring = str


class QArgumentParser(QtWidgets.QWidget):
    """User interface arguments

    Arguments:
        arguments (list, optional): Instances of QArgument
        description (str, optional): Long-form text of what this parser is for
        storage (QSettings, optional): Persistence to disk, providing
            value() and setValue() methods

    """

    changed = QtCore.Signal(QtCore.QObject)  # A QArgument

    def __init__(self,
                 arguments=None,
                 description=None,
                 storage=None,
                 parent=None):
        super(QArgumentParser, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)

        # Create internal settings
        if storage is True:
            storage = QtCore.QSettings(
                QtCore.QSettings.IniFormat,
                QtCore.QSettings.UserScope,
                __name__, "QArgparse",
            )

        if storage is not None:
            _log.info("Storing settings @ %s" % storage.fileName())

        arguments = arguments or []

        assert hasattr(arguments, "__iter__"), "arguments must be iterable"
        assert isinstance(storage, (type(None), QtCore.QSettings)), (
            "storage must be of type QSettings"
        )

        layout = QtWidgets.QGridLayout(self)
        layout.setRowStretch(999, 1)

        if description:
            layout.addWidget(QtWidgets.QLabel(description), 0, 0, 1, 2)

        self._row = 1
        self._storage = storage
        self._arguments = odict()
        self._desciption = description

        for arg in arguments or []:
            self._addArgument(arg)

        self.setStyleSheet(style)

    def setDescription(self, text):
        self._desciption.setText(text)

    def addArgument(self, name, type=None, default=None, **kwargs):
        # Infer type from default
        if type is None and default is not None:
            type = _type(default)

        # Default to string
        type = type or str

        Argument = {
            None: String,
            int: Integer,
            float: Float,
            bool: Boolean,
            str: String,
            list: Enum,
            tuple: Enum,
        }.get(type, type)

        arg = Argument(name, default=default, **kwargs)
        self._addArgument(arg)
        return arg

    def _addArgument(self, arg):
        if arg["name"] in self._arguments:
            raise ValueError("Duplicate argument '%s'" % arg["name"])

        if self._storage is not None:
            default = self._storage.value(arg["name"])

            if default:
                if isinstance(arg, Boolean):
                    default = bool({
                        None: QtCore.Qt.Unchecked,

                        0: QtCore.Qt.Unchecked,
                        1: QtCore.Qt.Checked,
                        2: QtCore.Qt.Checked,

                        "0": QtCore.Qt.Unchecked,
                        "1": QtCore.Qt.Checked,
                        "2": QtCore.Qt.Checked,

                        # May be stored as string, if used with IniFormat
                        "false": QtCore.Qt.Unchecked,
                        "true": QtCore.Qt.Checked,
                    }.get(default))

                arg["default"] = default

        arg.changed.connect(lambda: self.on_changed(arg))

        label = (
            QtWidgets.QLabel(arg["label"])
            if arg.label
            else QtWidgets.QLabel()
        )
        widget = arg.create()
        icon = qtawesome.icon("fa.refresh", color="white")
        reset = QtWidgets.QPushButton(icon, "")  # default
        reset.setToolTip("Reset")
        reset.setProperty("type", "reset")
        reset.clicked.connect(lambda: self.on_reset(arg))

        # Shown on edit
        reset.hide()

        for widget in (label, widget):
            widget.setToolTip(arg["help"])
            widget.setObjectName(arg["name"])  # useful in CSS
            widget.setProperty("type", type(arg).__name__)
            widget.setAttribute(QtCore.Qt.WA_StyledBackground)
            widget.setEnabled(arg["enabled"])

        # Align label on top of row if widget is over two times heiger
        height = (lambda w: w.sizeHint().height())
        label_on_top = height(label) * 2 < height(widget)
        alignment = (QtCore.Qt.AlignTop,) if label_on_top else ()

        layout = self.layout()
        layout.addWidget(label, self._row, 0, *alignment)
        layout.addWidget(widget, self._row, 1)
        layout.addWidget(reset, self._row, 2, *alignment)
        layout.setColumnStretch(1, 1)

        def on_changed(*_):
            reset.setVisible(arg["edited"])

        arg.changed.connect(on_changed)

        self._row += 1
        self._arguments[arg["name"]] = arg

    def clear(self):
        assert self._storage, "Cannot clear without persistent storage"
        self._storage.clear()
        _log.info("Clearing settings @ %s" % self._storage.fileName())

    def find(self, name):
        return self._arguments[name]

    def on_reset(self, arg):
        arg.write(arg["default"])

    def on_changed(self, arg):
        arg["edited"] = arg.read() != arg["default"]
        self.changed.emit(arg)

    # Optional PEP08 syntax
    add_argument = addArgument


class QArgument(QtCore.QObject):
    """Base class of argument user interface
    """
    changed = QtCore.Signal()

    # Provide a left-hand side label for this argument
    label = True
    # For defining default value for each argument type
    default = None

    def __init__(self, name, default=None, **kwargs):
        super(QArgument, self).__init__(kwargs.pop("parent", None))

        kwargs["name"] = name
        kwargs["label"] = kwargs.get("label", camel_to_title(name))
        kwargs["default"] = self.default if default is None else default
        kwargs["help"] = kwargs.get("help", "")
        kwargs["read"] = kwargs.get("read")
        kwargs["write"] = kwargs.get("write")
        kwargs["enabled"] = bool(kwargs.get("enabled", True))
        kwargs["edited"] = False

        self._data = kwargs

    def __str__(self):
        return self["name"]

    def __repr__(self):
        return "%s(\"%s\")" % (type(self).__name__, self["name"])

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __eq__(self, other):
        if isinstance(other, _basestring):
            return self["name"] == other
        return super(QArgument, self).__eq__(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def create(self):
        return QtWidgets.QWidget()

    def read(self):
        return self._read()

    def write(self, value):
        self._write(value)
        self.changed.emit()


class Boolean(QArgument):
    """Boolean type user interface

    Presented by `QtWidgets.QCheckBox`.

    Arguments:
        name (str): The name of argument
        label (str, optional): Display name, convert from `name` if not given
        help (str, optional): Tool tip message of this argument
        default (bool, optional): Argument's default value, default None
        enabled (bool, optional): Whether to enable this widget, default True

    """
    def create(self):
        widget = QtWidgets.QCheckBox()
        widget.clicked.connect(self.changed.emit)

        if isinstance(self, Tristate):
            self._read = lambda: widget.checkState()
            state = {
                0: QtCore.Qt.Unchecked,
                1: QtCore.Qt.PartiallyChecked,
                2: QtCore.Qt.Checked,
                "1": QtCore.Qt.PartiallyChecked,
                "0": QtCore.Qt.Unchecked,
                "2": QtCore.Qt.Checked,
            }
        else:
            self._read = lambda: bool(widget.checkState())
            state = {
                None: QtCore.Qt.Unchecked,

                0: QtCore.Qt.Unchecked,
                1: QtCore.Qt.Checked,
                2: QtCore.Qt.Checked,

                "0": QtCore.Qt.Unchecked,
                "1": QtCore.Qt.Checked,
                "2": QtCore.Qt.Checked,

                # May be stored as string, if used with QSettings(..IniFormat)
                "false": QtCore.Qt.Unchecked,
                "true": QtCore.Qt.Checked,
            }

        self._write = lambda value: widget.setCheckState(state[value])
        widget.clicked.connect(self.changed.emit)

        if self["default"] is not None:
            self._write(self["default"])

        return widget

    def read(self):
        return self._read()


class Tristate(QArgument):
    """Not implemented"""


class Number(QArgument):
    """Base class of numeric type user interface"""
    default = 0

    def create(self):
        if isinstance(self, Float):
            widget = QtWidgets.QDoubleSpinBox()
            widget.setMinimum(self._data.get("min", 0.0))
            widget.setMaximum(self._data.get("max", 99.99))
        else:
            widget = QtWidgets.QSpinBox()
            widget.setMinimum(self._data.get("min", 0))
            widget.setMaximum(self._data.get("max", 99))

        widget.editingFinished.connect(self.changed.emit)
        self._read = lambda: widget.value()
        self._write = lambda value: widget.setValue(value)

        if self["default"] != self.default:
            self._write(self["default"])

        return widget


class Integer(Number):
    """Integer type user interface

    A subclass of `qargparse.Number`, presented by `QtWidgets.QSpinBox`.

    Arguments:
        name (str): The name of argument
        label (str, optional): Display name, convert from `name` if not given
        help (str, optional): Tool tip message of this argument
        default (int, optional): Argument's default value, default 0
        min (int, optional): Argument's minimum value, default 0
        max (int, optional): Argument's maximum value, default 99
        enabled (bool, optional): Whether to enable this widget, default True

    """


class Float(Number):
    """Float type user interface

    A subclass of `qargparse.Number`, presented by `QtWidgets.QDoubleSpinBox`.

    Arguments:
        name (str): The name of argument
        label (str, optional): Display name, convert from `name` if not given
        help (str, optional): Tool tip message of this argument
        default (float, optional): Argument's default value, default 0.0
        min (float, optional): Argument's minimum value, default 0.0
        max (float, optional): Argument's maximum value, default 99.99
        enabled (bool, optional): Whether to enable this widget, default True

    """


class Range(Number):
    """Range type user interface

    A subclass of `qargparse.Number`, not production ready.

    """


class Double3(QArgument):
    """Double3 type user interface

    Presented by three `QtWidgets.QLineEdit` widget with `QDoubleValidator`
    installed.

    Arguments:
        name (str): The name of argument
        label (str, optional): Display name, convert from `name` if not given
        help (str, optional): Tool tip message of this argument
        default (tuple or list, optional): Default (0, 0, 0).
        enabled (bool, optional): Whether to enable this widget, default True

    """
    default = (0, 0, 0)

    def create(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        x, y, z = (self.child_arg(layout, i) for i in range(3))

        self._read = lambda: (
            float(x.text()), float(y.text()), float(z.text()))
        self._write = lambda value: [
            w.setText(str(float(v))) for w, v in zip([x, y, z], value)]

        if self["default"] != self.default:
            self._write(self["default"])

        return widget

    def child_arg(self, layout, index):
        widget = QtWidgets.QLineEdit()
        widget.setValidator(QtGui.QDoubleValidator())

        default = str(float(self["default"][index]))
        widget.setText(default)

        def focusOutEvent(event):
            if not widget.text():
                widget.setText(default)  # Ensure value exists for `_read`
            QtWidgets.QLineEdit.focusOutEvent(widget, event)
        widget.focusOutEvent = focusOutEvent

        widget.editingFinished.connect(self.changed.emit)
        widget.returnPressed.connect(widget.editingFinished.emit)

        layout.addWidget(widget)

        return widget


class String(QArgument):
    """String type user interface

    Presented by `QtWidgets.QLineEdit`.

    Arguments:
        name (str): The name of argument
        label (str, optional): Display name, convert from `name` if not given
        help (str, optional): Tool tip message of this argument
        default (str, optional): Argument's default value, default None
        placeholder (str, optional): Placeholder message for the widget
        enabled (bool, optional): Whether to enable this widget, default True

    """
    def __init__(self, *args, **kwargs):
        super(String, self).__init__(*args, **kwargs)
        self._previous = None

    def create(self):
        widget = QtWidgets.QLineEdit()
        widget.editingFinished.connect(self.onEditingFinished)
        widget.returnPressed.connect(widget.editingFinished.emit)
        self._read = lambda: widget.text()
        self._write = lambda value: widget.setText(value)

        if isinstance(self, Info):
            widget.setReadOnly(True)
        widget.setPlaceholderText(self._data.get("placeholder", ""))

        if self["default"] is not None:
            self._write(self["default"])
            self._previous = self["default"]

        return widget

    def onEditingFinished(self):
        current = self._read()

        if current != self._previous:
            self.changed.emit()
            self._previous = current


class Info(String):
    """String type user interface but read-only

    A subclass of `qargparse.String`, presented by `QtWidgets.QLineEdit`.

    Arguments:
        name (str): The name of argument
        label (str, optional): Display name, convert from `name` if not given
        help (str, optional): Tool tip message of this argument
        default (str, optional): Argument's default value, default None
        enabled (bool, optional): Whether to enable this widget, default True

    """


class Color(String):
    """Color type user interface

    A subclass of `qargparse.String`, not production ready.

    """


class Button(QArgument):
    """Button type user interface

    Presented by `QtWidgets.QPushButton`.

    Arguments:
        name (str): The name of argument
        label (str, optional): Display name, convert from `name` if not given
        help (str, optional): Tool tip message of this argument
        default (bool, optional): Argument's default value, default None
        enabled (bool, optional): Whether to enable this widget, default True

    """
    label = False

    def create(self):
        widget = QtWidgets.QPushButton(self["label"])
        widget.clicked.connect(self.changed.emit)

        state = [
            QtCore.Qt.Unchecked,
            QtCore.Qt.Checked,
        ]

        if isinstance(self, Toggle):
            widget.setCheckable(True)
            if hasattr(widget, "isChecked"):
                self._read = lambda: state[int(widget.isChecked())]
                self._write = (
                    lambda value: widget.setChecked(value)
                )
            else:
                self._read = lambda: widget.checkState()
                self._write = (
                    lambda value: widget.setCheckState(state[int(value)])
                )
        else:
            self._read = lambda: "clicked"
            self._write = lambda value: None

        if self["default"] is not None:
            self._write(self["default"])

        return widget


class Toggle(Button):
    """Checkable `Button` type user interface

    Presented by `QtWidgets.QPushButton`.

    Arguments:
        name (str): The name of argument
        label (str, optional): Display name, convert from `name` if not given
        help (str, optional): Tool tip message of this argument
        default (bool, optional): Argument's default value, default None
        enabled (bool, optional): Whether to enable this widget, default True

    """


class InfoList(QArgument):
    """String list type user interface

    Presented by `QtWidgets.QListView`, not production ready.

    """
    def __init__(self, name, **kwargs):
        kwargs["default"] = kwargs.pop("default", ["Empty"])
        super(InfoList, self).__init__(name, **kwargs)

    def create(self):
        class Model(QtCore.QStringListModel):
            def data(self, index, role):
                return super(Model, self).data(index, role)

        model = QtCore.QStringListModel(self["default"])
        widget = QtWidgets.QListView()
        widget.setModel(model)
        widget.setEditTriggers(widget.NoEditTriggers)

        self._read = lambda: model.stringList()
        self._write = lambda value: model.setStringList(value)

        return widget


class Choice(QArgument):
    """Argument user interface for selecting one from list

    Presented by `QtWidgets.QListView`.

    Arguments:
        name (str): The name of argument
        label (str, optional): Display name, convert from `name` if not given
        help (str, optional): Tool tip message of this argument
        items (list, optional): List of strings for select, default `["Empty"]`
        default (str, optional): Default item in `items`, use first of `items`
            if not given.
        enabled (bool, optional): Whether to enable this widget, default True

    """
    def __init__(self, name, **kwargs):
        kwargs["items"] = kwargs.get("items", ["Empty"])
        kwargs["default"] = kwargs.pop("default", kwargs["items"][0])
        super(Choice, self).__init__(name, **kwargs)

    def index(self, value):
        """Return numerical equivalent to self.read()"""
        return self["items"].index(value)

    def create(self):
        def on_changed(selected, deselected):
            try:
                selected = selected.indexes()[0]
            except IndexError:
                # At least one item must be selected at all times
                selected = deselected.indexes()[0]

            value = selected.data(QtCore.Qt.DisplayRole)
            set_current(value)
            self.changed.emit()

        def set_current(current):
            options = model.stringList()

            if current == "Empty":
                index = 0
            else:
                for index, member in enumerate(options):
                    if member == current:
                        break
                else:
                    raise ValueError(
                        "%s not a member of %s" % (current, options)
                    )

            qindex = model.index(index, 0, QtCore.QModelIndex())
            smodel.setCurrentIndex(qindex, smodel.ClearAndSelect)
            self["current"] = options[index]

        def reset(items, default=None):
            items = items or ["Empty"]
            model.setStringList(items)
            set_current(default or items[0])

        model = QtCore.QStringListModel()
        widget = QtWidgets.QListView()
        widget.setModel(model)
        widget.setEditTriggers(widget.NoEditTriggers)
        widget.setSelectionMode(widget.SingleSelection)
        smodel = widget.selectionModel()
        smodel.selectionChanged.connect(on_changed)

        self._read = lambda: self["current"]
        self._write = lambda value: set_current(value)
        self.reset = reset

        reset(self["items"], self["default"])

        return widget


class Separator(QArgument):
    """Visual separator

    Example:

        item1
        item2
        ------------
        item3
        item4

    """

    def create(self):
        widget = QtWidgets.QWidget()

        self._read = lambda: None
        self._write = lambda value: None

        return widget


class Enum(QArgument):
    """Argument user interface for selecting one from dropdown list

    Presented by `QtWidgets.QComboBox`.

    Arguments:
        name (str): The name of argument
        label (str, optional): Display name, convert from `name` if not given
        help (str, optional): Tool tip message of this argument
        items (list, optional): List of strings for select, default `[]`
        default (int, optional): Index of default item, use first of `items`
            if not given.
        enabled (bool, optional): Whether to enable this widget, default True

    """
    def __init__(self, name, **kwargs):
        kwargs["default"] = kwargs.pop("default", 0)
        kwargs["items"] = kwargs.get("items", [])

        assert isinstance(kwargs["items"], (tuple, list)), (
            "items must be list"
        )

        super(Enum, self).__init__(name, **kwargs)

    def create(self):
        widget = QtWidgets.QComboBox()
        widget.addItems(self["items"])
        widget.currentIndexChanged.connect(
            lambda index: self.changed.emit())

        self._read = lambda: widget.currentText()
        self._write = lambda value: widget.setCurrentIndex(value)

        if self["default"] is not None:
            self._write(self["default"])

        return widget


style = """\
QWidget {
    /* Explicitly specify a size, to account for automatic HDPi */
    font-size: 11px;
}

*[type="Button"] {
    text-align:left;
}

*[type="Info"] {
    background: transparent;
    border: none;
}

QLabel[type="Separator"] {
    min-height: 20px;
    text-decoration: underline;
}

QPushButton[type="reset"] {
    max-width: 11px;
    max-height: 11px;
}

"""


def camelToTitle(text):
    """Convert camelCase `text` to Title Case

    Example:
        >>> camelToTitle("mixedCase")
        "Mixed Case"
        >>> camelToTitle("myName")
        "My Name"
        >>> camelToTitle("you")
        "You"
        >>> camelToTitle("You")
        "You"
        >>> camelToTitle("This is That")
        "This Is That"

    """

    return re.sub(
        r"((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))",
        r" \1", text
    ).title()


camel_to_title = camelToTitle


def _demo():
    import sys
    app = QtWidgets.QApplication(sys.argv)

    parser = QArgumentParser()
    parser.setWindowTitle("Demo")
    parser.setMinimumWidth(300)

    parser.add_argument("name", default="Marcus", help="Your name")
    parser.add_argument("age", default=33, help="Your age")
    parser.add_argument("height", default=1.87, help="Your height")
    parser.add_argument("alive", default=True, help="Your state")
    parser.add_argument("class", type=Enum, items=[
        "Ranger",
        "Warrior",
        "Sorcerer",
        "Monk",
    ], default=2, help="Your class")

    parser.add_argument("options", type=Separator)
    parser.add_argument("paths", type=InfoList, items=[
        "Value A",
        "Value B",
        "Some other value",
        "And finally, value C",
    ])
    parser.add_argument("location", type=Double3)

    parser.show()
    app.exec_()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--demo", action="store_true")

    opts = parser.parse_args()

    if opts.demo:
        _demo()

    if opts.version:
        print(__version__)
