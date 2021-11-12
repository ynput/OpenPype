import re
import inspect

from Qt import QtWidgets, QtCore, QtGui

from avalon.vendor import qtawesome

from .constants import (
    PluginRole,
    FamilyRole,
    SubsetAllowedSymbols
)


class CreateErrorMessageBox(QtWidgets.QDialog):
    def __init__(
        self,
        family,
        subset_name,
        asset_name,
        exc_msg,
        formatted_traceback,
        parent=None
    ):
        super(CreateErrorMessageBox, self).__init__(parent)
        self.setWindowTitle("Creation failed")
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setWindowFlags(
            self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
        )

        body_layout = QtWidgets.QVBoxLayout(self)

        main_label = (
            "<span style='font-size:18pt;'>Failed to create</span>"
        )
        main_label_widget = QtWidgets.QLabel(main_label, self)
        body_layout.addWidget(main_label_widget)

        item_name_template = (
            "<span style='font-weight:bold;'>Family:</span> {}<br>"
            "<span style='font-weight:bold;'>Subset:</span> {}<br>"
            "<span style='font-weight:bold;'>Asset:</span> {}<br>"
        )
        exc_msg_template = "<span style='font-weight:bold'>{}</span>"

        line = self._create_line()
        body_layout.addWidget(line)

        item_name = item_name_template.format(family, subset_name, asset_name)
        item_name_widget = QtWidgets.QLabel(
            item_name.replace("\n", "<br>"), self
        )
        body_layout.addWidget(item_name_widget)

        exc_msg = exc_msg_template.format(exc_msg.replace("\n", "<br>"))
        message_label_widget = QtWidgets.QLabel(exc_msg, self)
        body_layout.addWidget(message_label_widget)

        if formatted_traceback:
            tb_widget = QtWidgets.QLabel(
                formatted_traceback.replace("\n", "<br>"), self
            )
            tb_widget.setTextInteractionFlags(
                QtCore.Qt.TextBrowserInteraction
            )
            body_layout.addWidget(tb_widget)

        footer_widget = QtWidgets.QWidget(self)
        footer_layout = QtWidgets.QHBoxLayout(footer_widget)
        button_box = QtWidgets.QDialogButtonBox(QtCore.Qt.Vertical)
        button_box.setStandardButtons(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        )
        button_box.accepted.connect(self._on_accept)
        footer_layout.addWidget(button_box, alignment=QtCore.Qt.AlignRight)
        body_layout.addWidget(footer_widget)

    def _on_accept(self):
        self.close()

    def _create_line(self):
        line = QtWidgets.QFrame(self)
        line.setFixedHeight(2)
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        return line


class SubsetNameValidator(QtGui.QRegExpValidator):
    invalid = QtCore.Signal(set)
    pattern = "^[{}]*$".format(SubsetAllowedSymbols)

    def __init__(self):
        reg = QtCore.QRegExp(self.pattern)
        super(SubsetNameValidator, self).__init__(reg)

    def validate(self, text, pos):
        results = super(SubsetNameValidator, self).validate(text, pos)
        if results[0] == self.Invalid:
            self.invalid.emit(self.invalid_chars(text))
        return results

    def invalid_chars(self, text):
        invalid = set()
        re_valid = re.compile(self.pattern)
        for char in text:
            if char == " ":
                invalid.add("' '")
                continue
            if not re_valid.match(char):
                invalid.add(char)
        return invalid


class VariantLineEdit(QtWidgets.QLineEdit):
    report = QtCore.Signal(str)
    colors = {
        "empty": (QtGui.QColor("#78879b"), ""),
        "exists": (QtGui.QColor("#4E76BB"), "border-color: #4E76BB;"),
        "new": (QtGui.QColor("#7AAB8F"), "border-color: #7AAB8F;"),
    }

    def __init__(self, *args, **kwargs):
        super(VariantLineEdit, self).__init__(*args, **kwargs)

        validator = SubsetNameValidator()
        self.setValidator(validator)
        self.setToolTip("Only alphanumeric characters (A-Z a-z 0-9), "
                        "'_' and '.' are allowed.")

        self._status_color = self.colors["empty"][0]

        anim = QtCore.QPropertyAnimation()
        anim.setTargetObject(self)
        anim.setPropertyName(b"status_color")
        anim.setEasingCurve(QtCore.QEasingCurve.InCubic)
        anim.setDuration(300)
        anim.setStartValue(QtGui.QColor("#C84747"))  # `Invalid` status color
        self.animation = anim

        validator.invalid.connect(self.on_invalid)

    def on_invalid(self, invalid):
        message = "Invalid character: %s" % ", ".join(invalid)
        self.report.emit(message)
        self.animation.stop()
        self.animation.start()

    def as_empty(self):
        self._set_border("empty")
        self.report.emit("Empty subset name ..")

    def as_exists(self):
        self._set_border("exists")
        self.report.emit("Existing subset, appending next version.")

    def as_new(self):
        self._set_border("new")
        self.report.emit("New subset, creating first version.")

    def _set_border(self, status):
        qcolor, style = self.colors[status]
        self.animation.setEndValue(qcolor)
        self.setStyleSheet(style)

    def _get_status_color(self):
        return self._status_color

    def _set_status_color(self, color):
        self._status_color = color
        self.setStyleSheet("border-color: %s;" % color.name())

    status_color = QtCore.Property(
        QtGui.QColor, _get_status_color, _set_status_color
    )


class FamilyDescriptionWidget(QtWidgets.QWidget):
    """A family description widget.

    Shows a family icon, family name and a help description.
    Used in creator header.

     _________________
    |  ____           |
    | |icon| FAMILY   |
    | |____| help     |
    |_________________|

    """

    SIZE = 35

    def __init__(self, parent=None):
        super(FamilyDescriptionWidget, self).__init__(parent=parent)

        # Header font
        font = QtGui.QFont()
        font.setBold(True)
        font.setPointSize(14)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        icon = QtWidgets.QLabel()
        icon.setSizePolicy(QtWidgets.QSizePolicy.Maximum,
                           QtWidgets.QSizePolicy.Maximum)

        # Add 4 pixel padding to avoid icon being cut off
        icon.setFixedWidth(self.SIZE + 4)
        icon.setFixedHeight(self.SIZE + 4)
        icon.setStyleSheet("""
        QLabel {
            padding-right: 5px;
        }
        """)

        label_layout = QtWidgets.QVBoxLayout()
        label_layout.setSpacing(0)

        family = QtWidgets.QLabel("family")
        family.setFont(font)
        family.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeft)

        help = QtWidgets.QLabel("help")
        help.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)

        label_layout.addWidget(family)
        label_layout.addWidget(help)

        layout.addWidget(icon)
        layout.addLayout(label_layout)

        self.help = help
        self.family = family
        self.icon = icon

    def set_item(self, item):
        """Update elements to display information of a family item.

        Args:
            item (dict): A family item as registered with name, help and icon

        Returns:
            None

        """
        if not item:
            return

        # Support a font-awesome icon
        plugin = item.data(PluginRole)
        icon_name = getattr(plugin, "icon", None) or "info-circle"
        try:
            icon = qtawesome.icon("fa.{}".format(icon_name), color="white")
            pixmap = icon.pixmap(self.SIZE, self.SIZE)
        except Exception:
            print("BUG: Couldn't load icon \"fa.{}\"".format(str(icon_name)))
            # Create transparent pixmap
            pixmap = QtGui.QPixmap()
            pixmap.fill(QtCore.Qt.transparent)
        pixmap = pixmap.scaled(self.SIZE, self.SIZE)

        # Parse a clean line from the Creator's docstring
        docstring = inspect.getdoc(plugin)
        help = docstring.splitlines()[0] if docstring else ""

        self.icon.setPixmap(pixmap)
        self.family.setText(item.data(FamilyRole))
        self.help.setText(help)
