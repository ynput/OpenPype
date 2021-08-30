from Qt import QtWidgets, QtCore, QtGui


class NiceSlider(QtWidgets.QSlider):
    def __init__(self, *args, **kwargs):
        super(NiceSlider, self).__init__(*args, **kwargs)
        self._mouse_clicked = False
        self._handle_size = 0

        self._bg_brush = QtGui.QBrush(QtGui.QColor("#21252B"))
        self._fill_brush = QtGui.QBrush(QtGui.QColor("#5cadd6"))

    def mousePressEvent(self, event):
        self._mouse_clicked = True
        if event.button() == QtCore.Qt.LeftButton:
            self._set_value_to_pos(event.pos())
            return event.accept()
        return super(NiceSlider, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._mouse_clicked:
            self._set_value_to_pos(event.pos())

        super(NiceSlider, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._mouse_clicked = True
        super(NiceSlider, self).mouseReleaseEvent(event)

    def _set_value_to_pos(self, pos):
        if self.orientation() == QtCore.Qt.Horizontal:
            self._set_value_to_pos_x(pos.x())
        else:
            self._set_value_to_pos_y(pos.y())

    def _set_value_to_pos_x(self, pos_x):
        _range = self.maximum() - self.minimum()
        handle_size = self._handle_size
        half_handle = handle_size / 2
        pos_x -= half_handle
        width = self.width() - handle_size
        value = ((_range * pos_x) / width) + self.minimum()
        self.setValue(value)

    def _set_value_to_pos_y(self, pos_y):
        _range = self.maximum() - self.minimum()
        handle_size = self._handle_size
        half_handle = handle_size / 2
        pos_y = self.height() - pos_y - half_handle
        height = self.height() - handle_size
        value = (_range * pos_y / height) + self.minimum()
        self.setValue(value)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        opt = QtWidgets.QStyleOptionSlider()
        self.initStyleOption(opt)

        painter.fillRect(event.rect(), QtCore.Qt.transparent)

        painter.setRenderHint(QtGui.QPainter.HighQualityAntialiasing)

        horizontal = self.orientation() == QtCore.Qt.Horizontal

        rect = self.style().subControlRect(
            QtWidgets.QStyle.CC_Slider,
            opt,
            QtWidgets.QStyle.SC_SliderGroove,
            self
        )

        _range = self.maximum() - self.minimum()
        _offset = self.value() - self.minimum()
        if horizontal:
            _handle_half = rect.height() / 2
            _handle_size = _handle_half * 2
            width = rect.width() - _handle_size
            pos_x = ((width / _range) * _offset)
            pos_y = rect.center().y() - _handle_half + 1
        else:
            _handle_half = rect.width() / 2
            _handle_size = _handle_half * 2
            height = rect.height() - _handle_size
            pos_x = rect.center().x() - _handle_half + 1
            pos_y = height - ((height / _range) * _offset)

        handle_rect = QtCore.QRect(
            pos_x, pos_y, _handle_size, _handle_size
        )

        self._handle_size = _handle_size
        _offset = 2
        _size = _handle_size - _offset
        if horizontal:
            if rect.height() > _size:
                new_rect = QtCore.QRect(0, 0, rect.width(), _size)
                center_point = QtCore.QPoint(
                    rect.center().x(), handle_rect.center().y()
                )
                new_rect.moveCenter(center_point)
                rect = new_rect

            ratio = rect.height() / 2
            fill_rect = QtCore.QRect(
                rect.x(),
                rect.y(),
                handle_rect.right() - rect.x(),
                rect.height()
            )

        else:
            if rect.width() > _size:
                new_rect = QtCore.QRect(0, 0, _size, rect.height())
                center_point = QtCore.QPoint(
                    handle_rect.center().x(), rect.center().y()
                )
                new_rect.moveCenter(center_point)
                rect = new_rect

            ratio = rect.width() / 2
            fill_rect = QtCore.QRect(
                rect.x(),
                handle_rect.y(),
                rect.width(),
                rect.height() - handle_rect.y(),
            )

        painter.save()
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(self._bg_brush)
        painter.drawRoundedRect(rect, ratio, ratio)

        painter.setBrush(self._fill_brush)
        painter.drawRoundedRect(fill_rect, ratio, ratio)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(self._fill_brush)
        painter.drawEllipse(handle_rect)
        painter.restore()
