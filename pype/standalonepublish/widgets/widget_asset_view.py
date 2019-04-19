from . import QtCore
from . import DeselectableTreeView


class AssetView(DeselectableTreeView):
    """Item view.

    This implements a context menu.

    """

    def __init__(self):
        super(AssetView, self).__init__()
        self.setIndentation(15)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setHeaderHidden(True)
