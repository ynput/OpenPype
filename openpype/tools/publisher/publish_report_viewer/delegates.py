import collections
from Qt import QtWidgets, QtCore, QtGui
from .constants import (
    ITEM_IS_GROUP_ROLE,
    ITEM_ERRORED_ROLE,
    PLUGIN_SKIPPED_ROLE,
    PLUGIN_PASSED_ROLE,
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


class GroupItemDelegate(QtWidgets.QStyledItemDelegate):
    """Generic delegate for instance header"""

    _item_icons_by_name_and_size = collections.defaultdict(dict)

    _minus_pixmaps = {}
    _plus_pixmaps = {}
    _path_stroker = None

    _item_pix_offset_ratio = 1.0 / 5.0
    _item_border_size = 1.0 / 7.0
    _group_pix_offset_ratio = 1.0 / 3.0
    _group_pix_stroke_size_ratio = 1.0 / 7.0

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

        offset = int(size * cls._group_pix_offset_ratio)
        pnt_1 = QtCore.QPoint(offset, int(size / 2))
        pnt_2 = QtCore.QPoint(size - offset, int(size / 2))
        pnt_3 = QtCore.QPoint(int(size / 2), offset)
        pnt_4 = QtCore.QPoint(int(size / 2), size - offset)
        path_1 = QtGui.QPainterPath(pnt_1)
        path_1.lineTo(pnt_2)
        path_2 = QtGui.QPainterPath(pnt_3)
        path_2.lineTo(pnt_4)

        path_stroker = cls._get_path_stroker()
        path_stroker.setWidth(size * cls._group_pix_stroke_size_ratio)
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

        offset = int(size * cls._group_pix_offset_ratio)
        pnt_1 = QtCore.QPoint(offset, int(size / 2))
        pnt_2 = QtCore.QPoint(size - offset, int(size / 2))
        path = QtGui.QPainterPath(pnt_1)
        path.lineTo(pnt_2)
        path_stroker = cls._get_path_stroker()
        path_stroker.setWidth(size * cls._group_pix_stroke_size_ratio)
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

    @classmethod
    def _get_icon_color(cls, name):
        if name == "error":
            return QtGui.QColor(colors["error"])
        return QtGui.QColor(QtCore.Qt.white)

    @classmethod
    def _get_icon(cls, name, size):
        icons_by_size = cls._item_icons_by_name_and_size[name]
        if icons_by_size and size in icons_by_size:
            return icons_by_size[size]

        offset = int(size * cls._item_pix_offset_ratio)
        offset_size = size - (2 * offset)
        pix = QtGui.QPixmap(size, size)
        pix.fill(QtCore.Qt.transparent)

        painter = QtGui.QPainter(pix)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        draw_ellipse = True
        if name == "error":
            color = QtGui.QColor(colors["error"])
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(color)

        elif name == "skipped":
            color = QtGui.QColor(QtCore.Qt.white)
            pen = QtGui.QPen(color)
            pen.setWidth(int(size * cls._item_border_size))
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.transparent)

        elif name == "passed":
            color = QtGui.QColor(colors["ok"])
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(color)

        elif name == "removed":
            draw_ellipse = False

            offset = offset * 1.5
            p1 = QtCore.QPoint(offset, offset)
            p2 = QtCore.QPoint(size - offset, size - offset)
            p3 = QtCore.QPoint(offset, size - offset)
            p4 = QtCore.QPoint(size - offset, offset)

            pen = QtGui.QPen(QtCore.Qt.white)
            pen.setWidth(offset_size / 4)
            pen.setCapStyle(QtCore.Qt.RoundCap)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.transparent)
            painter.drawLine(p1, p2)
            painter.drawLine(p3, p4)

        else:
            color = QtGui.QColor(QtCore.Qt.white)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(color)

        if draw_ellipse:
            painter.drawEllipse(offset, offset, offset_size, offset_size)

        painter.end()

        cls._item_icons_by_name_and_size[name][size] = pix

        return pix

    def paint(self, painter, option, index):
        if index.data(ITEM_IS_GROUP_ROLE):
            self.group_item_paint(painter, option, index)
        else:
            self.item_paint(painter, option, index)

    def item_paint(self, painter, option, index):
        self.initStyleOption(option, index)

        widget = option.widget
        if widget:
            style = widget.style()
        else:
            style = QtWidgets.QApplicaion.style()

        style.proxy().drawPrimitive(
            style.PE_PanelItemViewItem, option, painter, widget
        )
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

        icon_size = expander_rect.height()
        if index.data(ITEM_ERRORED_ROLE):
            expander_icon = self._get_icon("error", icon_size)
        elif index.data(PLUGIN_SKIPPED_ROLE):
            expander_icon = self._get_icon("skipped", icon_size)
        elif index.data(PLUGIN_PASSED_ROLE):
            expander_icon = self._get_icon("passed", icon_size)
        elif index.data(INSTANCE_REMOVED_ROLE):
            expander_icon = self._get_icon("removed", icon_size)
        else:
            expander_icon = self._get_icon("", icon_size)

        label = index.data(QtCore.Qt.DisplayRole)
        label = option.fontMetrics.elidedText(
            label, QtCore.Qt.ElideRight, label_rect.width()
        )

        painter.save()
        # Draw icon
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

        expander_height = bg_rect.height()
        expander_width = expander_height + 5
        expander_y_offset = expander_height % 2
        expander_height -= expander_y_offset
        expander_rect = QtCore.QRectF(
            bg_rect.x(),
            bg_rect.y() + expander_y_offset,
            expander_width,
            expander_height
        )

        label_rect = QtCore.QRectF(
            bg_rect.x() + expander_width,
            bg_rect.y(),
            bg_rect.width() - expander_width,
            bg_rect.height()
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
            expander_icon = self._get_minus_pixmap(expander_height)
        else:
            expander_icon = self._get_plus_pixmap(expander_height)

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
