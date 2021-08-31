import platform
from Qt import QtWidgets, QtCore, QtGui
from constants import (
    ITEM_ID_ROLE,
    ITEM_IS_GROUP_ROLE,
    ITEM_LABEL_ROLE,
    PLUGIN_SKIPPED_ROLE,
    PLUGIN_ERRORED_ROLE,
    INSTANCE_REMOVED_ROLE
)

colors = {
    "error": QtGui.QColor("#ff4a4a"),
    "warning": QtGui.QColor("#ff9900"),
    "ok": QtGui.QColor("#77AE24"),
    "active": QtGui.QColor("#99CEEE"),
    "idle": QtCore.Qt.white,
    "inactive": QtGui.QColor("#888"),
    "hover": QtGui.QColor(255, 255, 255, 5),
    "selected": QtGui.QColor(255, 255, 255, 10),
    "outline": QtGui.QColor("#333"),
    "group": QtGui.QColor("#21252B"),
    "group-hover": QtGui.QColor("#3c3c3c"),
    "group-selected-hover": QtGui.QColor("#555555")
}


class ItemDelegate(QtWidgets.QStyledItemDelegate):
    pass


class GroupItemDelegate(QtWidgets.QStyledItemDelegate):
    """Generic delegate for instance header"""
    _minus_pixmaps = {}
    _plus_pixmaps = {}
    _path_stroker = None

    _pix_offset_ratio = 1 / 3
    _pix_stroke_size_ratio = 1 / 7

    def __init__(self, parent):
        super(GroupItemDelegate, self).__init__(parent)
        self.item_delegate = ItemDelegate(parent)

    @classmethod
    def _get_path_stroker(cls):
        if cls._path_stroker is None:
            path_stroker = QtGui.QPainterPathStroker()
            path_stroker.setCapStyle(QtCore.Qt.RoundCap)
            path_stroker.setJoinStyle(QtCore.Qt.RoundJoin)

            cls._path_stroker = path_stroker
        return cls._path_stroker

    @classmethod
    def _get_plus_pixmap(cls, size):
        pix = cls._minus_pixmaps.get(size)
        if pix is not None:
            return pix

        pix = QtGui.QPixmap(size, size)
        pix.fill(QtCore.Qt.transparent)

        offset = int(size * cls._pix_offset_ratio)
        pnt_1 = QtCore.QPoint(offset, int(size / 2))
        pnt_2 = QtCore.QPoint(size - offset, int(size / 2))
        pnt_3 = QtCore.QPoint(int(size / 2), offset)
        pnt_4 = QtCore.QPoint(int(size / 2), size - offset)
        path_1 = QtGui.QPainterPath(pnt_1)
        path_1.lineTo(pnt_2)
        path_2 = QtGui.QPainterPath(pnt_3)
        path_2.lineTo(pnt_4)

        path_stroker = cls._get_path_stroker()
        path_stroker.setWidth(size * cls._pix_stroke_size_ratio)
        stroked_path_1 = path_stroker.createStroke(path_1)
        stroked_path_2 = path_stroker.createStroke(path_2)

        pix = QtGui.QPixmap(size, size)
        pix.fill(QtCore.Qt.transparent)

        painter = QtGui.QPainter(pix)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtCore.Qt.transparent)
        painter.setBrush(QtCore.Qt.white)
        painter.drawPath(stroked_path_1)
        painter.drawPath(stroked_path_2)
        painter.end()

        cls._minus_pixmaps[size] = pix

        return pix

    @classmethod
    def _get_minus_pixmap(cls, size):
        pix = cls._plus_pixmaps.get(size)
        if pix is not None:
            return pix

        offset = int(size * cls._pix_offset_ratio)
        pnt_1 = QtCore.QPoint(offset, int(size / 2))
        pnt_2 = QtCore.QPoint(size - offset, int(size / 2))
        path = QtGui.QPainterPath(pnt_1)
        path.lineTo(pnt_2)
        path_stroker = cls._get_path_stroker()
        path_stroker.setWidth(size * cls._pix_stroke_size_ratio)
        stroked_path = path_stroker.createStroke(path)

        pix = QtGui.QPixmap(size, size)
        pix.fill(QtCore.Qt.transparent)

        painter = QtGui.QPainter(pix)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtCore.Qt.transparent)
        painter.setBrush(QtCore.Qt.white)
        painter.drawPath(stroked_path)
        painter.end()

        cls._plus_pixmaps[size] = pix

        return pix

    def paint(self, painter, option, index):
        if index.data(ITEM_IS_GROUP_ROLE):
            self.group_item_paint(painter, option, index)
        else:
            self.item_delegate.paint(painter, option, index)

    def group_item_paint(self, painter, option, index):
        """Paint text
         _
        My label
        """
        self.initStyleOption(option, index)

        widget = option.widget
        if widget:
            style = widget.style()
        else:
            style = QtWidgets.QApplicaion.style()
        _rect = style.proxy().subElementRect(
            style.SE_ItemViewItemText, option, widget
        )

        bg_rect = QtCore.QRectF(option.rect)
        bg_rect.setY(_rect.y())
        bg_rect.setHeight(_rect.height())

        expander_rect = QtCore.QRectF(bg_rect)
        expander_rect.setWidth(expander_rect.height() + 5)

        label_rect = QtCore.QRectF(
            expander_rect.x() + expander_rect.width(),
            expander_rect.y(),
            bg_rect.width() - expander_rect.width(),
            expander_rect.height()
        )

        bg_path = QtGui.QPainterPath()
        radius = (bg_rect.height() / 2) - 0.01
        bg_path.addRoundedRect(bg_rect, radius, radius)

        painter.fillPath(bg_path, colors["group"])

        selected = option.state & QtWidgets.QStyle.State_Selected
        hovered = option.state & QtWidgets.QStyle.State_MouseOver

        if selected and hovered:
            painter.fillPath(bg_path, colors["selected"])
        elif hovered:
            painter.fillPath(bg_path, colors["hover"])

        expanded = self.parent().isExpanded(index)
        if expanded:
            expander_icon = self._get_minus_pixmap(expander_rect.height())
        else:
            expander_icon = self._get_plus_pixmap(expander_rect.height())

        label = index.data(QtCore.Qt.DisplayRole)
        label = option.fontMetrics.elidedText(
            label, QtCore.Qt.ElideRight, label_rect.width()
        )

        # Maintain reference to state, so we can restore it once we're done
        painter.save()
        pix_point = QtCore.QPoint(
            expander_rect.center().x() - int(expander_icon.width() / 2),
            expander_rect.top()
        )
        painter.drawPixmap(pix_point, expander_icon)

        # Draw label
        painter.setFont(option.font)
        painter.drawText(label_rect, QtCore.Qt.AlignVCenter, label)

        # Ok, we're done, tidy up.
        painter.restore()
