import qtpy
from qtpy import QtWidgets, QtCore, QtGui


class PickScreenColorWidget(QtWidgets.QWidget):
    color_selected = QtCore.Signal(QtGui.QColor)

    def __init__(self, parent=None):
        super(PickScreenColorWidget, self).__init__(parent)
        self.labels = []
        self.magnification = 2

        self._min_magnification = 1
        self._max_magnification = 10

    def add_magnification_delta(self, delta):
        _delta = abs(delta / 1000)
        if delta > 0:
            self.magnification += _delta
        else:
            self.magnification -= _delta

        if self.magnification > self._max_magnification:
            self.magnification = self._max_magnification
        elif self.magnification < self._min_magnification:
            self.magnification = self._min_magnification

    def pick_color(self):
        if self.labels:
            if self.labels[0].isVisible():
                return
            self.labels = []

        for screen in QtWidgets.QApplication.screens():
            label = PickLabel(self)
            label.pick_color(screen)
            label.color_selected.connect(self.on_color_select)
            label.close_session.connect(self.end_pick_session)
            self.labels.append(label)

    def end_pick_session(self):
        for label in self.labels:
            label.close()
        self.labels = []

    def on_color_select(self, color):
        self.color_selected.emit(color)
        self.end_pick_session()


class PickLabel(QtWidgets.QLabel):
    color_selected = QtCore.Signal(QtGui.QColor)
    close_session = QtCore.Signal()

    def __init__(self, pick_widget):
        super(PickLabel, self).__init__()
        self.setMouseTracking(True)

        self.pick_widget = pick_widget

        self.radius_pen = QtGui.QPen(QtGui.QColor(27, 27, 27), 2)
        self.text_pen = QtGui.QPen(QtGui.QColor(127, 127, 127), 4)
        self.text_bg = QtGui.QBrush(QtGui.QColor(27, 27, 27))
        self._mouse_over = False

        self.radius = 100
        self.radius_ratio = 11

    @property
    def magnification(self):
        return self.pick_widget.magnification

    def pick_color(self, screen_obj):
        self.show()
        self.windowHandle().setScreen(screen_obj)
        geo = screen_obj.geometry()
        args = (
            QtWidgets.QApplication.desktop().winId(),
            geo.x(), geo.y(), geo.width(), geo.height()
        )
        if qtpy.API in ("pyqt4", "pyside"):
            pix = QtGui.QPixmap.grabWindow(*args)
        else:
            pix = screen_obj.grabWindow(*args)

        if pix.width() > pix.height():
            size = pix.height()
        else:
            size = pix.width()

        self.radius = int(size / self.radius_ratio)

        self.setPixmap(pix)
        self.showFullScreen()

    def wheelEvent(self, event):
        y_delta = event.angleDelta().y()
        self.pick_widget.add_magnification_delta(y_delta)
        self.update()

    def enterEvent(self, event):
        self._mouse_over = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._mouse_over = False
        super().leaveEvent(event)
        self.update()

    def mouseMoveEvent(self, event):
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._mouse_over:
            return

        mouse_pos_to_widet = self.mapFromGlobal(QtGui.QCursor.pos())

        magnified_half_size = self.radius / self.magnification
        magnified_size = magnified_half_size * 2

        zoom_x_1 = mouse_pos_to_widet.x() - magnified_half_size
        zoom_x_2 = mouse_pos_to_widet.x() + magnified_half_size
        zoom_y_1 = mouse_pos_to_widet.y() - magnified_half_size
        zoom_y_2 = mouse_pos_to_widet.y() + magnified_half_size
        pix_width = magnified_size
        pix_height = magnified_size
        draw_pos_x = 0
        draw_pos_y = 0
        if zoom_x_1 < 0:
            draw_pos_x = abs(zoom_x_1)
            pix_width -= draw_pos_x
            zoom_x_1 = 1
        elif zoom_x_2 > self.pixmap().width():
            pix_width -= zoom_x_2 - self.pixmap().width()

        if zoom_y_1 < 0:
            draw_pos_y = abs(zoom_y_1)
            pix_height -= draw_pos_y
            zoom_y_1 = 1
        elif zoom_y_2 > self.pixmap().height():
            pix_height -= zoom_y_2 - self.pixmap().height()

        new_pix = QtGui.QPixmap(magnified_size, magnified_size)
        new_pix.fill(QtCore.Qt.transparent)
        new_pix_painter = QtGui.QPainter(new_pix)
        new_pix_painter.drawPixmap(
            QtCore.QRect(draw_pos_x, draw_pos_y, pix_width, pix_height),
            self.pixmap().copy(zoom_x_1, zoom_y_1, pix_width, pix_height)
        )
        new_pix_painter.end()

        painter = QtGui.QPainter(self)

        ellipse_rect = QtCore.QRect(
            mouse_pos_to_widet.x() - self.radius,
            mouse_pos_to_widet.y() - self.radius,
            self.radius * 2,
            self.radius * 2
        )
        ellipse_rect_f = QtCore.QRectF(ellipse_rect)
        path = QtGui.QPainterPath()
        path.addEllipse(ellipse_rect_f)
        painter.setClipPath(path)

        new_pix_rect = QtCore.QRect(
            mouse_pos_to_widet.x() - self.radius + 1,
            mouse_pos_to_widet.y() - self.radius + 1,
            new_pix.width() * self.magnification,
            new_pix.height() * self.magnification
        )

        painter.drawPixmap(new_pix_rect, new_pix)

        painter.setClipping(False)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        painter.setPen(self.radius_pen)
        painter.drawEllipse(ellipse_rect_f)

        image = self.pixmap().toImage()
        if image.valid(mouse_pos_to_widet):
            color = QtGui.QColor(image.pixel(mouse_pos_to_widet))
        else:
            color = QtGui.QColor()

        color_text = "Red: {} - Green: {} - Blue: {}".format(
            color.red(), color.green(), color.blue()
        )
        font = painter.font()
        font.setPointSize(self.radius / 10)
        painter.setFont(font)

        text_rect_height = int(painter.fontMetrics().height() + 10)
        text_rect = QtCore.QRect(
            ellipse_rect.x(),
            ellipse_rect.bottom(),
            ellipse_rect.width(),
            text_rect_height
        )
        if text_rect.bottom() > self.pixmap().height():
            text_rect.moveBottomLeft(ellipse_rect.topLeft())

        rect_radius = text_rect_height / 2
        path = QtGui.QPainterPath()
        path.addRoundedRect(
            QtCore.QRectF(text_rect),
            rect_radius,
            rect_radius
        )
        painter.fillPath(path, self.text_bg)

        painter.setPen(self.text_pen)
        painter.drawText(
            text_rect,
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignCenter,
            color_text
        )

        color_rect_x = ellipse_rect.x() - text_rect_height
        if color_rect_x < 0:
            color_rect_x += (text_rect_height + ellipse_rect.width())

        color_rect = QtCore.QRect(
            color_rect_x,
            ellipse_rect.y(),
            text_rect_height,
            ellipse_rect.height()
        )
        path = QtGui.QPainterPath()
        path.addRoundedRect(
            QtCore.QRectF(color_rect),
            rect_radius,
            rect_radius
        )
        painter.fillPath(path, color)
        painter.drawRoundedRect(color_rect, rect_radius, rect_radius)
        painter.end()

    def mouseReleaseEvent(self, event):
        color = QtGui.QColor(self.pixmap().toImage().pixel(event.pos()))
        self.color_selected.emit(color)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.close_session.emit()
