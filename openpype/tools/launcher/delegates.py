import time
from Qt import QtCore, QtWidgets, QtGui
from .constants import (
    ANIMATION_START_ROLE,
    ANIMATION_STATE_ROLE,
    FORCE_NOT_OPEN_WORKFILE_ROLE
)


class ActionDelegate(QtWidgets.QStyledItemDelegate):
    extender_lines = 2
    extender_bg_brush = QtGui.QBrush(QtGui.QColor(100, 100, 100, 160))
    extender_fg = QtGui.QColor(255, 255, 255, 160)

    def __init__(self, group_roles, *args, **kwargs):
        super(ActionDelegate, self).__init__(*args, **kwargs)
        self.group_roles = group_roles
        self._anim_start_color = QtGui.QColor(178, 255, 246)
        self._anim_end_color = QtGui.QColor(5, 44, 50)

    def _draw_animation(self, painter, option, index):
        grid_size = option.widget.gridSize()
        x_offset = int(
            (grid_size.width() / 2)
            - (option.rect.width() / 2)
        )
        item_x = option.rect.x() - x_offset
        rect_offset = grid_size.width() / 20
        size = grid_size.width() - (rect_offset * 2)
        anim_rect = QtCore.QRect(
            item_x + rect_offset,
            option.rect.y() + rect_offset,
            size,
            size
        )

        painter.save()

        painter.setBrush(QtCore.Qt.transparent)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        gradient = QtGui.QConicalGradient()
        gradient.setCenter(anim_rect.center())
        gradient.setColorAt(0, self._anim_start_color)
        gradient.setColorAt(1, self._anim_end_color)

        time_diff = time.time() - index.data(ANIMATION_START_ROLE)

        # Repeat 4 times
        part_anim = 2.5
        part_time = time_diff % part_anim
        offset = (part_time / part_anim) * 360
        angle = (offset + 90) % 360

        gradient.setAngle(-angle)

        pen = QtGui.QPen(QtGui.QBrush(gradient), rect_offset)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(
            anim_rect,
            -16 * (angle + 10),
            -16 * offset
        )

        painter.restore()

    def paint(self, painter, option, index):
        if index.data(ANIMATION_STATE_ROLE):
            self._draw_animation(painter, option, index)

        super(ActionDelegate, self).paint(painter, option, index)

        if index.data(FORCE_NOT_OPEN_WORKFILE_ROLE):
            rect = QtCore.QRectF(option.rect.x(), option.rect.height(),
                                 5, 5)
            painter.setPen(QtCore.Qt.transparent)
            painter.setBrush(QtGui.QColor(200, 0, 0))
            painter.drawEllipse(rect)

            painter.setBrush(self.extender_bg_brush)

        is_group = False
        for group_role in self.group_roles:
            is_group = index.data(group_role)
            if is_group:
                break
        if not is_group:
            return

        grid_size = option.widget.gridSize()
        x_offset = int(
            (grid_size.width() / 2)
            - (option.rect.width() / 2)
        )
        item_x = option.rect.x() - x_offset

        tenth_width = int(grid_size.width() / 10)
        tenth_height = int(grid_size.height() / 10)

        extender_width = tenth_width * 2
        extender_height = tenth_height * 2

        exteder_rect = QtCore.QRectF(
            item_x + tenth_width,
            option.rect.y() + tenth_height,
            extender_width,
            extender_height
        )
        path = QtGui.QPainterPath()
        path.addRoundedRect(exteder_rect, 2, 2)

        painter.fillPath(path, self.extender_bg_brush)

        painter.setPen(self.extender_fg)
        painter.drawPath(path)

        divider = (2 * self.extender_lines) + 1
        extender_offset = int(extender_width / 6)
        line_height = round(extender_height / divider)
        line_width = extender_width - (extender_offset * 2) + 1
        pos_x = exteder_rect.x() + extender_offset
        pos_y = exteder_rect.y() + line_height
        for _ in range(self.extender_lines):
            line_rect = QtCore.QRectF(
                pos_x, pos_y, line_width, line_height
            )
            painter.fillRect(line_rect, self.extender_fg)
            pos_y += 2 * line_height
