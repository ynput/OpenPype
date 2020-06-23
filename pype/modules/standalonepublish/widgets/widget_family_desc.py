import os
import sys
import inspect
import json

from . import QtWidgets, QtCore, QtGui
from . import HelpRole, FamilyRole, ExistsRole, PluginRole
from . import qtawesome
import six
from pype import lib as pypelib


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
            family (dict): A family item as registered with name, help and icon

        Returns:
            None

        """
        if not item:
            return

        # Support a font-awesome icon
        plugin = item.data(PluginRole)
        icon = getattr(plugin, "icon", "info-circle")
        assert isinstance(icon, six.string_types)
        icon = qtawesome.icon("fa.{}".format(icon), color="white")
        pixmap = icon.pixmap(self.SIZE, self.SIZE)
        pixmap = pixmap.scaled(self.SIZE, self.SIZE)

        # Parse a clean line from the Creator's docstring
        docstring = plugin.help or ""

        help = docstring.splitlines()[0] if docstring else ""

        self.icon.setPixmap(pixmap)
        self.family.setText(item.data(FamilyRole))
        self.help.setText(help)
