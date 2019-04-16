from avalon.vendor.Qt import *
from avalon.vendor import qtawesome as awesome
from avalon import style

HelpRole = QtCore.Qt.UserRole + 2
FamilyRole = QtCore.Qt.UserRole + 3
ExistsRole = QtCore.Qt.UserRole + 4
PluginRole = QtCore.Qt.UserRole + 5

from ..resources import get_resource
from .button_from_svgs import SvgResizable, SvgButton
