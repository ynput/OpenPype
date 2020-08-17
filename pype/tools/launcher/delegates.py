from Qt import QtCore, QtWidgets, QtGui


class ActionDelegate(QtWidgets.QStyledItemDelegate):
    extender_lines = 2
    extender_bg_brush = QtGui.QBrush(QtGui.QColor(100, 100, 100, 160))
    extender_fg = QtGui.QColor(255, 255, 255, 160)

    def __init__(self, group_roles, *args, **kwargs):
        super(ActionDelegate, self).__init__(*args, **kwargs)
        self.group_roles = group_roles

    def paint(self, painter, option, index):
        super(ActionDelegate, self).paint(painter, option, index)
        is_group = False
        for group_role in self.group_roles:
            is_group = index.data(group_role)
            if is_group:
                break
        if not is_group:
            return

        extender_width = int(option.decorationSize.width() / 2)
        extender_height = int(option.decorationSize.height() / 2)

        exteder_rect = QtCore.QRectF(
            option.rect.x() + (option.rect.width() / 10),
            option.rect.y() + (option.rect.height() / 10),
            extender_width,
            extender_height
        )
        path = QtGui.QPainterPath()
        path.addRoundedRect(exteder_rect, 2, 2)

        painter.fillPath(path, self.extender_bg_brush)

        painter.setPen(self.extender_fg)
        painter.drawPath(path)

        divider = (2 * self.extender_lines) + 1
        line_height = extender_height / divider
        line_width = extender_width - (extender_width / 5)
        pos_x = exteder_rect.x() + extender_width / 10
        pos_y = exteder_rect.y() + line_height
        for _ in range(self.extender_lines):
            line_rect = QtCore.QRectF(
                pos_x, pos_y, line_width, round(line_height)
            )
            painter.fillRect(line_rect, self.extender_fg)
            pos_y += 2 * line_height
