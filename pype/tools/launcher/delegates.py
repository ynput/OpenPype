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
