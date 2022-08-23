from enum import Enum
from math import floor, ceil, sqrt, sin, cos, acos, pi as PI
from Qt import QtWidgets, QtCore, QtGui

TWOPI = PI * 2


class TriangleState(Enum):
    IdleState = object()
    SelectingHueState = object()
    SelectingSatValueState = object()


class DoubleColor:
    def __init__(self, r, g=None, b=None):
        if g is None:
            g = r.g
            b = r.b
            r = r.r
        self.r = float(r)
        self.g = float(g)
        self.b = float(b)


class Vertex:
    def __init__(self, color, point):
        # Convert GlobalColor to QColor as globals don't have red, green, blue
        if isinstance(color, QtCore.Qt.GlobalColor):
            color = QtGui.QColor(color)

        # Convert QColor to DoubleColor
        if isinstance(color, QtGui.QColor):
            color = DoubleColor(color.red(), color.green(), color.blue())

        self.color = color
        self.point = point


class QtColorTriangle(QtWidgets.QWidget):
    """The QtColorTriangle class provides a triangular color selection widget.

    This widget uses the HSV color model, and is therefore useful for
    selecting colors by eye.

    The triangle in the center of the widget is used for selecting
    saturation and value, and the surrounding circle is used for
    selecting hue.

    Use set_color() and color() to set and get the current color.
    """
    color_changed = QtCore.Signal(QtGui.QColor)

    # Thick of color wheel ratio where 1 is fully filled circle
    inner_radius_ratio = 5.0
    # Ratio where hue selector on wheel is relative to `inner_radius_ratio`
    # - middle of the wheel is twice `inner_radius_ratio`
    selector_radius_ratio = inner_radius_ratio * 2
    # Size ratio of selectors on wheel and in triangle
    ellipse_size_ratio = 10.0
    # Ration of selectors thickness
    ellipse_thick_ratio = 50.0
    # Hue offset on color wheel (0 - 359)
    # - red on top if set to "0"
    hue_offset = 90

    def __init__(self, parent=None):
        super(QtColorTriangle, self).__init__(parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum
        )
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.angle_a = float()
        self.angle_b = float()
        self.angle_c = float()

        self.bg_image = QtGui.QImage(
            self.sizeHint(), QtGui.QImage.Format_RGB32
        )
        self.cur_color = QtGui.QColor()
        self.point_a = QtCore.QPointF()
        self.point_b = QtCore.QPointF()
        self.point_c = QtCore.QPointF()
        self.point_d = QtCore.QPointF()

        self.cur_hue = int()

        self.pen_width = int()
        self.ellipse_size = int()
        self.outer_radius = int()
        self.selector_pos = QtCore.QPointF()

        self.sel_mode = TriangleState.IdleState

        self._triangle_outline_pen = QtGui.QPen(
            QtGui.QColor(40, 40, 40, 128),
            2
        )
        # Prepare hue numbers for color circle
        _hue_circle_range = []
        for idx in range(11):
            # Some Qt versions may require:
            # hue = int(idx * 360.0)
            percent_idx = idx * 0.1
            hue = int(360.0 - (percent_idx * 360.0))
            _hue_circle_range.append((percent_idx, hue))
        self._hue_circle_range = tuple(_hue_circle_range)

        color = QtGui.QColor()
        color.setHsv(0, 255, 255)
        self.set_color(color)

    def set_color(self, col):
        if (
            col.red() == self.cur_color.red()
            and col.green() == self.cur_color.green()
            and col.blue() == self.cur_color.blue()
        ):
            return

        self.cur_color = col

        hue, *_ = self.cur_color.getHsv()

        # Never use an invalid hue to display colors
        if hue != -1:
            self.cur_hue = hue

        angle_with_offset = (360 - self.cur_hue - self.hue_offset) % 360
        self.angle_a = (angle_with_offset * TWOPI) / 360.0
        self.angle_a += PI / 2.0
        if self.angle_a > TWOPI:
            self.angle_a -= TWOPI

        self.angle_b = self.angle_a + TWOPI / 3
        self.angle_c = self.angle_b + TWOPI / 3

        if self.angle_b > TWOPI:
            self.angle_b -= TWOPI
        if self.angle_c > TWOPI:
            self.angle_c -= TWOPI

        cx = float(self.contentsRect().center().x())
        cy = float(self.contentsRect().center().y())
        inner_radius = (
            self.outer_radius
            - (self.outer_radius / self.inner_radius_ratio)
        )
        selector_radius = (
            self.outer_radius
            - (self.outer_radius / self.selector_radius_ratio)
        )
        self.point_a = QtCore.QPointF(
            cx + (cos(self.angle_a) * inner_radius),
            cy - (sin(self.angle_a) * inner_radius)
        )
        self.point_b = QtCore.QPointF(
            cx + (cos(self.angle_b) * inner_radius),
            cy - (sin(self.angle_b) * inner_radius)
        )
        self.point_c = QtCore.QPointF(
            cx + (cos(self.angle_c) * inner_radius),
            cy - (sin(self.angle_c) * inner_radius)
        )
        self.point_d = QtCore.QPointF(
            cx + (cos(self.angle_a) * selector_radius),
            cy - (sin(self.angle_a) * selector_radius)
        )

        self.selector_pos = self._point_from_color(self.cur_color)
        self.update()

        self.color_changed.emit(self.cur_color)

    def heightForWidth(self, width):
        return width

    def polish(self):
        size_w = self.contentsRect().width()
        size_h = self.contentsRect().height()
        if size_w < size_h:
            size = size_w
        else:
            size = size_h

        self.outer_radius = (size - 1) / 2

        self.pen_width = int(
            ceil(self.outer_radius / self.ellipse_thick_ratio)
        )
        self.ellipse_size = int(
            ceil(self.outer_radius / self.ellipse_size_ratio)
        )

        cx = float(self.contentsRect().center().x())
        cy = float(self.contentsRect().center().y())

        inner_radius = (
            self.outer_radius
            - (self.outer_radius / self.inner_radius_ratio)
        )
        selector_radius = (
            self.outer_radius
            - (self.outer_radius / self.selector_radius_ratio)
        )
        self.point_a = QtCore.QPointF(
            cx + (cos(self.angle_a) * inner_radius),
            cy - (sin(self.angle_a) * inner_radius)
        )
        self.point_b = QtCore.QPointF(
            cx + (cos(self.angle_b) * inner_radius),
            cy - (sin(self.angle_b) * inner_radius)
        )
        self.point_c = QtCore.QPointF(
            cx + (cos(self.angle_c) * inner_radius),
            cy - (sin(self.angle_c) * inner_radius)
        )
        self.point_d = QtCore.QPointF(
            cx + (cos(self.angle_a) * selector_radius),
            cy - (sin(self.angle_a) * selector_radius)
        )

        self.selector_pos = self._point_from_color(self.cur_color)

        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        if event.rect().intersects(self.contentsRect()):
            event_region = event.region()
            if hasattr(event_region, "intersect"):
                clip_region = event_region.intersect(self.contentsRect())
            else:
                clip_region = event_region.intersected(
                    self.contentsRect()
                )
            painter.setClipRegion(clip_region)

        self.paint_bg()

        # Blit the static generated background with the hue gradient onto
        # the double buffer.
        buf = QtGui.QImage(
            self.bg_image.width(),
            self.bg_image.height(),
            QtGui.QImage.Format_RGB32
        )

        # Draw the trigon
        # Find the color with only the hue, and max value and saturation
        hue_color = QtGui.QColor()
        hue_color.setHsv(self.cur_hue, 255, 255)

        # Draw the triangle
        self.drawTrigon(
            buf, self.point_a, self.point_b, self.point_c, hue_color
        )

        # Slow step: convert the image to a pixmap
        pix = self.bg_image.copy()
        pix_painter = QtGui.QPainter(pix)

        pix_painter.setRenderHint(QtGui.QPainter.HighQualityAntialiasing)

        trigon_path = QtGui.QPainterPath()
        trigon_path.moveTo(self.point_a)
        trigon_path.lineTo(self.point_b)
        trigon_path.lineTo(self.point_c)
        trigon_path.closeSubpath()
        pix_painter.setClipPath(trigon_path)

        pix_painter.drawImage(0, 0, buf)

        pix_painter.setClipping(False)

        # Draw an outline of the triangle
        pix_painter.setPen(self._triangle_outline_pen)
        pix_painter.drawLine(self.point_a, self.point_b)
        pix_painter.drawLine(self.point_b, self.point_c)
        pix_painter.drawLine(self.point_c, self.point_a)

        # Draw the color wheel selector
        pix_painter.setPen(QtGui.QPen(QtCore.Qt.white, self.pen_width))
        pix_painter.drawEllipse(
            int(self.point_d.x() - self.ellipse_size / 2.0),
            int(self.point_d.y() - self.ellipse_size / 2.0),
            self.ellipse_size, self.ellipse_size
        )

        # Draw the triangle selector
        pix_painter.setBrush(self.cur_color)
        pix_painter.drawEllipse(
            QtCore.QRectF(
                self.selector_pos.x() - self.ellipse_size / 2.0,
                self.selector_pos.y() - self.ellipse_size / 2.0,
                self.ellipse_size + 0.5,
                self.ellipse_size + 0.5
            )
        )

        pix_painter.end()
        # Blit
        painter.drawPixmap(self.contentsRect().topLeft(), pix)
        painter.end()

    def mouseMoveEvent(self, event):
        if (event.buttons() & QtCore.Qt.LeftButton) == 0:
            return

        depos = QtCore.QPointF(
            event.pos().x(),
            event.pos().y()
        )
        new_color = False

        if self.sel_mode is TriangleState.SelectingHueState:
            self.angle_a = self._angle_at(depos, self.contentsRect())
            self.angle_b = self.angle_a + (TWOPI / 3.0)
            self.angle_c = self.angle_b + (TWOPI / 3.0)
            if self.angle_b > TWOPI:
                self.angle_b -= TWOPI
            if self.angle_c > TWOPI:
                self.angle_c -= TWOPI

            am = self.angle_a - (PI / 2)
            if am < 0:
                am += TWOPI
            self.cur_hue = (
                360 - int((am * 360.0) / TWOPI) - self.hue_offset
            ) % 360
            hue, sat, val, _ = self.cur_color.getHsv()

            if self.cur_hue != hue:
                new_color = True
                self.cur_color.setHsv(self.cur_hue, sat, val)

            cx = float(self.contentsRect().center().x())
            cy = float(self.contentsRect().center().y())
            inner_radius = (
                self.outer_radius
                - (self.outer_radius / self.inner_radius_ratio)
            )
            selector_radius = (
                self.outer_radius
                - (self.outer_radius / self.selector_radius_ratio)
            )
            self.point_a = QtCore.QPointF(
                cx + (cos(self.angle_a) * inner_radius),
                cy - (sin(self.angle_a) * inner_radius)
            )
            self.point_b = QtCore.QPointF(
                cx + (cos(self.angle_b) * inner_radius),
                cy - (sin(self.angle_b) * inner_radius)
            )
            self.point_c = QtCore.QPointF(
                cx + (cos(self.angle_c) * inner_radius),
                cy - (sin(self.angle_c) * inner_radius)
            )
            self.point_d = QtCore.QPointF(
                cx + (cos(self.angle_a) * selector_radius),
                cy - (sin(self.angle_a) * selector_radius)
            )

            self.selector_pos = self._point_from_color(self.cur_color)
        else:
            aa = Vertex(QtCore.Qt.transparent, self.point_a)
            bb = Vertex(QtCore.Qt.transparent, self.point_b)
            cc = Vertex(QtCore.Qt.transparent, self.point_c)

            self.selector_pos = self._move_point_to_triangle(
                depos.x(), depos.y(), aa, bb, cc
            )
            col = self._color_from_point(self.selector_pos)
            if col != self.cur_color:
                # Ensure that hue does not change when selecting
                # saturation and value.
                _, sat, val, _ = col.getHsv()
                self.cur_color.setHsv(self.cur_hue, sat, val)
                new_color = True

        if new_color:
            self.color_changed.emit(self.cur_color)

        self.update()

    def mousePressEvent(self, event):
        # Only respond to the left mouse button.
        if event.button() != QtCore.Qt.LeftButton:
            return

        depos = QtCore.QPointF(
            event.pos().x(),
            event.pos().y()
        )
        rad = self._radius_at(depos, self.contentsRect())
        new_color = False

        # As in mouseMoveEvent, either find the a, b, c angles or the
        # radian position of the selector, then order an update.
        inner_radius = (
            self.outer_radius - (self.outer_radius / self.inner_radius_ratio)
        )
        if rad > inner_radius:
            self.sel_mode = TriangleState.SelectingHueState

            self.angle_a = self._angle_at(depos, self.contentsRect())
            self.angle_b = self.angle_a + TWOPI / 3.0
            self.angle_c = self.angle_b + TWOPI / 3.0
            if self.angle_b > TWOPI:
                self.angle_b -= TWOPI
            if self.angle_c > TWOPI:
                self.angle_c -= TWOPI

            am = self.angle_a - PI / 2
            if am < 0:
                am += TWOPI

            self.cur_hue = (
                360 - int((am * 360.0) / TWOPI) - self.hue_offset
            ) % 360
            hue, sat, val, _ = self.cur_color.getHsv()

            if hue != self.cur_hue:
                new_color = True
                self.cur_color.setHsv(self.cur_hue, sat, val)

            cx = float(self.contentsRect().center().x())
            cy = float(self.contentsRect().center().y())

            self.point_a = QtCore.QPointF(
                cx + (cos(self.angle_a) * inner_radius),
                cy - (sin(self.angle_a) * inner_radius)
            )
            self.point_b = QtCore.QPointF(
                cx + (cos(self.angle_b) * inner_radius),
                cy - (sin(self.angle_b) * inner_radius)
            )
            self.point_c = QtCore.QPointF(
                cx + (cos(self.angle_c) * inner_radius),
                cy - (sin(self.angle_c) * inner_radius)
            )

            selector_radius = (
                self.outer_radius
                - (self.outer_radius / self.selector_radius_ratio)
            )
            self.point_d = QtCore.QPointF(
                cx + (cos(self.angle_a) * selector_radius),
                cy - (sin(self.angle_a) * selector_radius)
            )

            self.selector_pos = self._point_from_color(self.cur_color)
            self.color_changed.emit(self.cur_color)
        else:
            self.sel_mode = TriangleState.SelectingSatValueState

            aa = Vertex(QtCore.Qt.transparent, self.point_a)
            bb = Vertex(QtCore.Qt.transparent, self.point_b)
            cc = Vertex(QtCore.Qt.transparent, self.point_c)

            self.selector_pos = self._move_point_to_triangle(
                depos.x(), depos.y(), aa, bb, cc
            )
            col = self._color_from_point(self.selector_pos)
            if col != self.cur_color:
                self.cur_color = col
                new_color = True

        if new_color:
            self.color_changed.emit(self.cur_color)

        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.sel_mode = TriangleState.IdleState

    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Left:
            self.cur_hue -= 1
            if self.cur_hue < 0:
                self.cur_hue += 360
            _, sat, val, _ = self.cur_color.getHsv()

            tmp = QtGui.QColor()
            tmp.setHsv(self.cur_hue, sat, val)
            self.set_color(tmp)

        elif key == QtCore.Qt.Key_Right:
            self.cur_hue += 1
            if (self.cur_hue > 359):
                self.cur_hue -= 360
            _, sat, val, _ = self.cur_color.getHsv()
            tmp = QtGui.QColor()
            tmp.setHsv(self.cur_hue, sat, val)
            self.set_color(tmp)

        elif key == QtCore.Qt.Key_Up:
            _, sat, val, _ = self.cur_color.getHsv()
            if event.modifiers() & QtCore.Qt.ShiftModifier:
                if sat > 5:
                    sat -= 5
                else:
                    sat = 0
            else:
                if val > 5:
                    val -= 5
                else:
                    val = 0

            tmp = QtGui.QColor()
            tmp.setHsv(self.cur_hue, sat, val)
            self.set_color(tmp)

        elif key == QtCore.Qt.Key_Down:
            _, sat, val, _ = self.cur_color.getHsv()
            if event.modifiers() & QtCore.Qt.ShiftModifier:
                if sat < 250:
                    sat += 5
                else:
                    sat = 255
            else:
                if val < 250:
                    val += 5
                else:
                    val = 255

            tmp = QtGui.QColor()
            tmp.setHsv(self.cur_hue, sat, val)
            self.set_color(tmp)

    def resizeEvent(self, _event):
        size_w = self.contentsRect().width()
        size_h = self.contentsRect().height()
        if size_w < size_h:
            size = size_w
        else:
            size = size_h

        self.outer_radius = (size - 1) / 2

        self.pen_width = int(
            ceil(self.outer_radius / self.ellipse_thick_ratio)
        )
        self.ellipse_size = int(
            ceil(self.outer_radius / self.ellipse_size_ratio)
        )

        cx = float(self.contentsRect().center().x())
        cy = float(self.contentsRect().center().y())
        inner_radius = (
            self.outer_radius
            - (self.outer_radius / self.inner_radius_ratio)
        )
        selector_radius = (
            self.outer_radius
            - (self.outer_radius / self.selector_radius_ratio)
        )
        self.point_a = QtCore.QPointF(
            cx + (cos(self.angle_a) * inner_radius),
            cy - (sin(self.angle_a) * inner_radius)
        )
        self.point_b = QtCore.QPointF(
            cx + (cos(self.angle_b) * inner_radius),
            cy - (sin(self.angle_b) * inner_radius)
        )
        self.point_c = QtCore.QPointF(
            cx + (cos(self.angle_c) * inner_radius),
            cy - (sin(self.angle_c) * inner_radius)
        )
        self.point_d = QtCore.QPointF(
            cx + (cos(self.angle_a) * selector_radius),
            cy - (sin(self.angle_a) * selector_radius)
        )

        # Find the current position of the selector
        self.selector_pos = self._point_from_color(self.cur_color)

        self.update()

    def drawTrigon(self, buf, pa, pb, pc, color):
        # Create three Vertex objects. A Vertex contains a double-point
        # coordinate and a color.
        # pa is the tip of the arrow
        # pb is the black corner
        # pc is the white corner
        p1 = Vertex(color, pa)
        p2 = Vertex(QtCore.Qt.black, pb)
        p3 = Vertex(QtCore.Qt.white, pc)

        # Sort. Make p1 above p2, which is above p3 (using y coordinate).
        # Bubble sorting is fastest here.
        if p1.point.y() > p2.point.y():
            p1, p2 = p2, p1
        if p1.point.y() > p3.point.y():
            p1, p3 = p3, p1
        if p2.point.y() > p3.point.y():
            p2, p3 = p3, p2

        # All the three y deltas are >= 0
        p1p2ydist = float(p2.point.y() - p1.point.y())
        p1p3ydist = float(p3.point.y() - p1.point.y())
        p2p3ydist = float(p3.point.y() - p2.point.y())
        p1p2xdist = float(p2.point.x() - p1.point.x())
        p1p3xdist = float(p3.point.x() - p1.point.x())
        p2p3xdist = float(p3.point.x() - p2.point.x())

        # The first x delta decides wether we have a lefty or a righty
        # trigon.
        lefty = p1p2xdist < 0

        # Left and right colors and X values. The key in this map is the
        # y values. Our goal is to fill these structures with all the
        # information needed to do a single pass top-to-bottom,
        # left-to-right drawing of the trigon.
        leftColors = {}
        rightColors = {}
        leftX = {}
        rightX = {}

        # Scan longy - find all left and right colors and X-values for
        # the tallest edge (p1-p3).
        # Initialize with known values
        x = p1.point.x()
        source = p1.color
        dest = p3.color
        r = source.r
        g = source.g
        b = source.b
        y1 = int(floor(p1.point.y()))
        y2 = int(floor(p3.point.y()))

        # Find slopes (notice that if the y dists are 0, we don't care
        # about the slopes)
        xdelta = 0.0
        rdelta = 0.0
        gdelta = 0.0
        bdelta = 0.0
        if p1p3ydist != 0.0:
            xdelta = p1p3xdist / p1p3ydist
            rdelta = (dest.r - r) / p1p3ydist
            gdelta = (dest.g - g) / p1p3ydist
            bdelta = (dest.b - b) / p1p3ydist

        # Calculate gradients using linear approximation
        for y in range(y1, y2):
            if lefty:
                rightColors[y] = DoubleColor(r, g, b)
                rightX[y] = x
            else:
                leftColors[y] = DoubleColor(r, g, b)
                leftX[y] = x

            r += rdelta
            g += gdelta
            b += bdelta
            x += xdelta

        # Scan top shorty - find all left and right colors and x-values
        # for the topmost of the two not-tallest short edges.
        x = p1.point.x()
        source = p1.color
        dest = p2.color
        r = source.r
        g = source.g
        b = source.b
        y1 = int(floor(p1.point.y()))
        y2 = int(floor(p2.point.y()))

        # Find slopes (notice that if the y dists are 0, we don't care
        # about the slopes)
        xdelta = 0.0
        rdelta = 0.0
        gdelta = 0.0
        bdelta = 0.0
        if p1p2ydist != 0.0:
            xdelta = p1p2xdist / p1p2ydist
            rdelta = (dest.r - r) / p1p2ydist
            gdelta = (dest.g - g) / p1p2ydist
            bdelta = (dest.b - b) / p1p2ydist

        # Calculate gradients using linear approximation
        for y in range(y1, y2):
            if lefty:
                leftColors[y] = DoubleColor(r, g, b)
                leftX[y] = x
            else:
                rightColors[y] = DoubleColor(r, g, b)
                rightX[y] = x

            r += rdelta
            g += gdelta
            b += bdelta
            x += xdelta

        # Scan bottom shorty - find all left and right colors and
        # x-values for the bottommost of the two not-tallest short edges.
        x = p2.point.x()
        source = p2.color
        dest = p3.color
        r = source.r
        g = source.g
        b = source.b
        y1 = int(floor(p2.point.y()))
        y2 = int(floor(p3.point.y()))

        # Find slopes (notice that if the y dists are 0, we don't care
        # about the slopes)
        xdelta = 0.0
        rdelta = 0.0
        gdelta = 0.0
        bdelta = 0.0
        if p2p3ydist != 0.0:
            xdelta = p2p3xdist / p2p3ydist
            rdelta = (dest.r - r) / p2p3ydist
            gdelta = (dest.g - g) / p2p3ydist
            bdelta = (dest.b - b) / p2p3ydist

        # Calculate gradients using linear approximation
        for y in range(y1, y2):
            if lefty:
                leftColors[y] = DoubleColor(r, g, b)
                leftX[y] = x
            else:
                rightColors[y] = DoubleColor(r, g, b)
                rightX[y] = x

            r += rdelta
            g += gdelta
            b += bdelta
            x += xdelta

        # Inner loop. For each y in the left map of x-values, draw one
        # line from left to right.
        p3yfloor = int(floor(p3.point.y()))
        p1yfloor = int(floor(p1.point.y()))
        for y in range(p1yfloor, p3yfloor):
            lx = leftX[y]
            rx = rightX[y]

            # if the xdist is 0, don't draw anything.
            xdist = rx - lx
            if xdist == 0.0:
                continue

            lxi = int(floor(lx))
            rxi = int(floor(rx))
            rc = rightColors[y]
            lc = leftColors[y]

            r = lc.r
            g = lc.g
            b = lc.b
            rdelta = (rc.r - r) / xdist
            gdelta = (rc.g - g) / xdist
            bdelta = (rc.b - b) / xdist

            # Draw 2 more pixels on left side for smoothing
            for x in range(lxi - 2, lxi):
                buf.setPixel(x, y, QtGui.qRgb(int(r), int(g), int(b)))

            # Inner loop 2. Draws the line from left to right.
            for x in range(lxi, rxi):
                buf.setPixel(x, y, QtGui.qRgb(int(r), int(g), int(b)))
                r += rdelta
                g += gdelta
                b += bdelta

            # Draw 2 more pixels on right side for smoothing
            for x in range(rxi, rxi + 3):
                buf.setPixel(x, y, QtGui.qRgb(int(r), int(g), int(b)))

    def _radius_at(self, pos, rect):
        mousexdist = pos.x() - float(rect.center().x())
        mouseydist = pos.y() - float(rect.center().y())
        return sqrt(mousexdist ** 2 + mouseydist ** 2)

    def _angle_at(self, pos, rect):
        mousexdist = pos.x() - float(rect.center().x())
        mouseydist = pos.y() - float(rect.center().y())
        mouserad = sqrt(mousexdist ** 2 + mouseydist ** 2)
        if mouserad == 0.0:
            return 0.0

        angle = acos(mousexdist / mouserad)
        if mouseydist >= 0:
            angle = TWOPI - angle

        return angle

    def _point_from_color(self, col):
        # Simplifications for the corner cases.
        if col == QtCore.Qt.black:
            return self.point_b
        elif col == QtCore.Qt.white:
            return self.point_c

        # Find the x and y slopes
        ab_deltax = self.point_b.x() - self.point_a.x()
        ab_deltay = self.point_b.y() - self.point_a.y()
        bc_deltax = self.point_c.x() - self.point_b.x()
        bc_deltay = self.point_c.y() - self.point_b.y()
        ac_deltax = self.point_c.x() - self.point_a.x()
        ac_deltay = self.point_c.y() - self.point_a.y()

        # Extract the h,s,v values of col.
        _, sat, val, _ = col.getHsv()

        # Find the line that passes through the triangle where the value
        # is equal to our color's value.
        p1 = self.point_a.x() + (ab_deltax * float(255 - val)) / 255.0
        q1 = self.point_a.y() + (ab_deltay * float(255 - val)) / 255.0
        p2 = self.point_b.x() + (bc_deltax * float(val)) / 255.0
        q2 = self.point_b.y() + (bc_deltay * float(val)) / 255.0

        # Find the line that passes through the triangle where the
        # saturation is equal to our color's value.
        p3 = self.point_a.x() + (ac_deltax * float(255 - sat)) / 255.0
        q3 = self.point_a.y() + (ac_deltay * float(255 - sat)) / 255.0
        p4 = self.point_b.x()
        q4 = self.point_b.y()

        # Find the intersection between these lines.
        if p1 != p2:
            a = (q2 - q1) / (p2 - p1)
            c = (q4 - q3) / (p4 - p3)
            b = q1 - a * p1
            d = q3 - c * p3

            x = (d - b) / (a - c)
            y = a * x + b
        else:
            x = p1
            p4_p3 = p4 - p3
            if p4_p3 == 0:
                y = 0
            else:
                y = q3 + (x - p3) * (q4 - q3) / p4_p3

        return QtCore.QPointF(x, y)

    def _color_from_point(self, p):
        # Find the outer radius of the hue gradient.
        size_w = self.contentsRect().width()
        size_h = self.contentsRect().height()
        if size_w < size_h:
            size = size_w
        else:
            size = size_h
        outer_radius = (size - 1) / 2

        # Find the center coordinates
        cx = float(self.contentsRect().center().x())
        cy = float(self.contentsRect().center().y())

        # Find the a, b and c from their angles, the center of the rect
        # and the radius of the hue gradient donut.
        inner_radius = outer_radius - (outer_radius / self.inner_radius_ratio)
        pa = QtCore.QPointF(
            cx + (cos(self.angle_a) * inner_radius),
            cy - (sin(self.angle_a) * inner_radius)
        )
        pb = QtCore.QPointF(
            cx + (cos(self.angle_b) * inner_radius),
            cy - (sin(self.angle_b) * inner_radius)
        )
        pc = QtCore.QPointF(
            cx + (cos(self.angle_c) * inner_radius),
            cy - (sin(self.angle_c) * inner_radius)
        )

        # Find the hue value from the angle of the 'a' point.
        angle = self.angle_a - PI / 2.0
        if angle < 0:
            angle += TWOPI
        hue = (
            360
            - int(floor((360.0 * angle) / TWOPI))
            - self.hue_offset
        ) % 360

        # Create the color of the 'a' corner point. We know that b is
        # black and c is white.
        color = QtGui.QColor()
        color.setHsv(hue, 255, 255)

        # See also drawTrigon(), which basically does exactly the same to
        # determine all colors in the trigon.
        p1 = Vertex(color, pa)
        p2 = Vertex(QtCore.Qt.black, pb)
        p3 = Vertex(QtCore.Qt.white, pc)

        # Make sure p1 is above p2, which is above p3.
        if p1.point.y() > p2.point.y():
            p1, p2 = p2, p1
        if p1.point.y() > p3.point.y():
            p1, p3 = p3, p1
        if p2.point.y() > p3.point.y():
            p2, p3 = p3, p2

        # Find the slopes of all edges in the trigon. All the three y
        # deltas here are positive because of the above sorting.
        p1p2ydist = p2.point.y() - p1.point.y()
        p1p3ydist = p3.point.y() - p1.point.y()
        p2p3ydist = p3.point.y() - p2.point.y()
        p1p2xdist = p2.point.x() - p1.point.x()
        p1p3xdist = p3.point.x() - p1.point.x()
        p2p3xdist = p3.point.x() - p2.point.x()

        # The first x delta decides wether we have a lefty or a righty
        # trigon. A lefty trigon has its tallest edge on the right hand
        # side of the trigon. The righty trigon has it on its left side.
        # This property determines wether the left or the right set of x
        # coordinates will be continuous.
        lefty = p1p2xdist < 0

        # Find whether the selector's y is in the first or second shorty,
        # counting from the top and downwards. This is used to find the
        # color at the selector point.
        firstshorty = (p.y() >= p1.point.y() and p.y() < p2.point.y())

        # From the y value of the selector's position, find the left and
        # right x values.
        if lefty:
            if firstshorty:
                if (floor(p1p2ydist) != 0.0):
                    leftx = (
                        p1.point.x()
                        + ((p1p2xdist * (p.y() - p1.point.y())) / p1p2ydist)
                    )
                else:
                    leftx = min(p1.point.x(), p2.point.x())

            else:
                if (floor(p2p3ydist) != 0.0):
                    leftx = (
                        p2.point.x()
                        + (p2p3xdist * (p.y() - p2.point.y())) / p2p3ydist
                    )
                else:
                    leftx = min(p2.point.x(), p3.point.x())

            rightx = (
                p1.point.x()
                + ((p1p3xdist * (p.y() - p1.point.y())) / p1p3ydist)
            )
        else:
            leftx = (
                p1.point.x()
                + ((p1p3xdist * (p.y() - p1.point.y())) / p1p3ydist)
            )
            if firstshorty:
                if floor(p1p2ydist) != 0.0:
                    rightx = (
                        p1.point.x()
                        + ((p1p2xdist * (p.y() - p1.point.y())) / p1p2ydist)
                    )
                else:
                    rightx = max(p1.point.x(), p2.point.x())

            else:
                if floor(p2p3ydist) != 0.0:
                    rightx = (
                        p2.point.x()
                        + ((p2p3xdist * (p.y() - p2.point.y())) / p2p3ydist)
                    )
                else:
                    rightx = max(p2.point.x(), p3.point.x())

        # Find the r,g,b values of the points on the trigon's edges that
        # are to the left and right of the selector.
        if firstshorty:
            if floor(p1p2ydist) != 0.0:
                p_p1_ratio = (p.y() - p1.point.y()) / p1p2ydist
                p2_p_ratio = (p2.point.y() - p.y()) / p1p2ydist
                rshort = (p2.color.r * p_p1_ratio) + (p1.color.r * p2_p_ratio)
                gshort = (p2.color.g * p_p1_ratio) + (p1.color.g * p2_p_ratio)
                bshort = (p2.color.b * p_p1_ratio) + (p1.color.b * p2_p_ratio)
            elif lefty:
                if p1.point.x() <= p2.point.x():
                    rshort = p1.color.r
                    gshort = p1.color.g
                    bshort = p1.color.b
                else:
                    rshort = p2.color.r
                    gshort = p2.color.g
                    bshort = p2.color.b

            else:
                if p1.point.x() > p2.point.x():
                    rshort = p1.color.r
                    gshort = p1.color.g
                    bshort = p1.color.b
                else:
                    rshort = p2.color.r
                    gshort = p2.color.g
                    bshort = p2.color.b

        else:
            if floor(p2p3ydist) != 0.0:
                p_p2_ratio = (p.y() - p2.point.y()) / p2p3ydist
                p3_p_ratio = (p3.point.y() - p.y()) / p2p3ydist
                rshort = (p3.color.r * p_p2_ratio) + (p2.color.r * p3_p_ratio)
                gshort = (p3.color.g * p_p2_ratio) + (p2.color.g * p3_p_ratio)
                bshort = (p3.color.b * p_p2_ratio) + (p2.color.b * p3_p_ratio)
            elif lefty:
                if p2.point.x() <= p3.point.x():
                    rshort = p2.color.r
                    gshort = p2.color.g
                    bshort = p2.color.b
                else:
                    rshort = p3.color.r
                    gshort = p3.color.g
                    bshort = p3.color.b

            else:
                if p2.point.x() > p3.point.x():
                    rshort = p2.color.r
                    gshort = p2.color.g
                    bshort = p2.color.b
                else:
                    rshort = p3.color.r
                    gshort = p3.color.g
                    bshort = p3.color.b

        # p1p3ydist is never 0
        p_p1_ratio = (p.y() - p1.point.y()) / p1p3ydist
        p3_p_ratio = (p3.point.y() - p.y()) / p1p3ydist
        rlong = (p3.color.r * p_p1_ratio) + (p1.color.r * p3_p_ratio)
        glong = (p3.color.g * p_p1_ratio) + (p1.color.g * p3_p_ratio)
        blong = (p3.color.b * p_p1_ratio) + (p1.color.b * p3_p_ratio)

        # rshort,gshort,bshort is the color on one of the shortys.
        # rlong,glong,blong is the color on the longy. So depending on
        # wether we have a lefty trigon or not, we can determine which
        # colors are on the left and right edge.
        if lefty:
            rl = rshort
            gl = gshort
            bl = bshort
            rr = rlong
            gr = glong
            br = blong
        else:
            rl = rlong
            gl = glong
            bl = blong
            rr = rshort
            gr = gshort
            br = bshort

        # Find the distance from the left x to the right x (xdist). Then
        # find the distances from the selector to each of these (saxdist
        # and saxdist2). These distances are used to find the color at
        # the selector.
        xdist = rightx - leftx
        saxdist = p.x() - leftx
        saxdist2 = xdist - saxdist

        # Now determine the r,g,b values of the selector using a linear
        # approximation.
        if xdist != 0.0:
            r = (saxdist2 * rl / xdist) + (saxdist * rr / xdist)
            g = (saxdist2 * gl / xdist) + (saxdist * gr / xdist)
            b = (saxdist2 * bl / xdist) + (saxdist * br / xdist)
        else:
            # In theory, the left and right color will be equal here. But
            # because of the loss of precision, we get an error on both
            # colors. The best approximation we can get is from adding
            # the two errors, which in theory will eliminate the error
            # but in practise will only minimize it.
            r = (rl + rr) / 2
            g = (gl + gr) / 2
            b = (bl + br) / 2

        # Now floor the color components and fit them into proper
        # boundaries. This again is to compensate for the error caused by
        # loss of precision.
        ri = int(floor(r))
        gi = int(floor(g))
        bi = int(floor(b))
        if ri < 0:
            ri = 0
        elif ri > 255:
            ri = 255

        if gi < 0:
            gi = 0
        elif gi > 255:
            gi = 255

        if bi < 0:
            bi = 0
        elif bi > 255:
            bi = 255

        # Voila, we have the color at the point of the selector.
        return QtGui.QColor(ri, gi, bi)

    def paint_bg(self):
        bg_image = QtGui.QPixmap(self.contentsRect().size())
        bg_image.fill(QtCore.Qt.transparent)
        self.bg_image = bg_image

        painter = QtGui.QPainter(self.bg_image)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        hue_gradient = QtGui.QConicalGradient(
            bg_image.rect().center(), 90 - self.hue_offset
        )
        sat_val_gradient = QtGui.QConicalGradient(
            bg_image.rect().center(), 90 - self.hue_offset
        )

        hue_color = QtGui.QColor()
        sat_val_color = QtGui.QColor()
        _, sat, val, _ = self.cur_color.getHsv()

        for idx, hue in self._hue_circle_range:
            hue_color.setHsv(hue, 255, 255)
            sat_val_color.setHsv(hue, sat, val)

            hue_gradient.setColorAt(idx, hue_color)
            sat_val_gradient.setColorAt(idx, sat_val_color)

        inner_radius = self.outer_radius - (
            self.outer_radius / self.inner_radius_ratio
        )
        half_radius = self.outer_radius - (
            (self.outer_radius - inner_radius) / 2
        )

        hue_inner_radius_rect = QtCore.QRectF(
            bg_image.rect().center().x() - inner_radius,
            bg_image.rect().center().y() - inner_radius,
            inner_radius * 2 + 1,
            inner_radius * 2 + 1
        )
        hue_outer_radius_rect = QtCore.QRectF(
            bg_image.rect().center().x() - half_radius - 1,
            bg_image.rect().center().y() - half_radius - 1,
            half_radius * 2 + 3,
            half_radius * 2 + 3
        )
        sat_val_inner_radius_rect = QtCore.QRectF(
            bg_image.rect().center().x() - half_radius,
            bg_image.rect().center().y() - half_radius,
            half_radius * 2 + 1,
            half_radius * 2 + 1
        )
        sat_val_outer_radius_rect = QtCore.QRectF(
            bg_image.rect().center().x() - self.outer_radius,
            bg_image.rect().center().y() - self.outer_radius,
            self.outer_radius * 2 + 1,
            self.outer_radius * 2 + 1
        )
        hue_path = QtGui.QPainterPath()
        hue_path.addEllipse(hue_inner_radius_rect)
        hue_path.addEllipse(hue_outer_radius_rect)

        sat_val_path = QtGui.QPainterPath()
        sat_val_path.addEllipse(sat_val_inner_radius_rect)
        sat_val_path.addEllipse(sat_val_outer_radius_rect)

        painter.save()
        painter.setClipPath(hue_path)
        painter.fillRect(self.bg_image.rect(), hue_gradient)
        painter.restore()

        painter.save()
        painter.setClipPath(sat_val_path)
        painter.fillRect(self.bg_image.rect(), sat_val_gradient)
        painter.restore()

        painter.end()

    @staticmethod
    def vlen(x, y):
        return sqrt((x ** 2) + (y ** 2))

    @staticmethod
    def vprod(x1, y1, x2, y2):
        return x1 * x2 + y1 * y2

    @staticmethod
    def _angle_between_angles(p, a1, a2):
        if a1 > a2:
            a2 += TWOPI
            if p < PI:
                p += TWOPI

        return p >= a1 and p < a2

    @staticmethod
    def _point_above_point(x, y, px, py, ax, ay, bx, by):
        floored_ax = floor(ax)
        floored_bx = floor(bx)
        floored_ay = floor(ay)
        floored_by = floor(by)

        if floored_ax == floored_bx:
            # line is vertical
            if floored_ay < floored_by:
                return x < ax
            elif floored_ay > floored_by:
                return x > ax
            return not (x == ax and y == ay)

        if floored_ax > floored_bx:
            if floored_ay < floored_by:
                # line is draw upright-to-downleft
                return (floor(x) < floor(px) or floor(y) < floor(py))
            elif floored_ay > floored_by:
                # line is draw downright-to-upleft
                return (floor(x) > floor(px) or floor(y) < floor(py))
            # line is flat horizontal
            return y < ay

        if floored_ay < floored_by:
            # line is draw upleft-to-downright
            return (floor(x) < floor(px) or floor(y) > floor(py))
        elif floored_ay > floored_by:
            # line is draw downleft-to-upright
            return (floor(x) > floor(px) or floor(y) > floor(py))
        # line is flat horizontal
        return y > ay

    @staticmethod
    def _point_in_line(x, y, ax, ay, bx, by):
        if ax > bx:
            if ay < by:
                # line is draw upright-to-downleft

                # if (x,y) is in on or above the upper right point,
                # return -1.
                if y <= ay and x >= ax:
                    return -1

                # if (x,y) is in on or below the lower left point,
                # return 1.
                if y >= by and x <= bx:
                    return 1
            else:
                # line is draw downright-to-upleft

                # If the line is flat, only use the x coordinate.
                if floor(ay) == floor(by):
                    # if (x is to the right of the rightmost point,
                    # return -1. otherwise if x is to the left of the
                    # leftmost point, return 1.
                    if x >= ax:
                        return -1
                    elif x <= bx:
                        return 1
                else:
                    # if (x,y) is on or below the lower right point,
                    # return -1.
                    if y >= ay and x >= ax:
                        return -1

                    # if (x,y) is on or above the upper left point, return 1.
                    if y <= by and x <= bx:
                        return 1
        else:
            if ay < by:
                # line is draw upleft-to-downright

                # If (x,y) is on or above the upper left point, return -1.
                if y <= ay and x <= ax:
                    return -1

                # If (x,y) is on or below the lower right point, return 1.
                if y >= by and x >= bx:
                    return 1
            else:
                # line is draw downleft-to-upright

                # If the line is flat, only use the x coordinate.
                if floor(ay) == floor(by):
                    if x <= ax:
                        return -1
                    elif x >= bx:
                        return 1
                else:
                    # If (x,y) is on or below the lower left point, return -1.
                    if y >= ay and x <= ax:
                        return -1

                    # If (x,y) is on or above the upper right point, return 1.
                    if y <= by and x >= bx:
                        return 1

        # No tests proved that (x,y) was outside [(ax,ay),(bx,by)], so we
        # assume it's inside the line's bounds.
        return 0

    def _move_point_to_triangle(self, x, y, a, b, c):
        # Let v1A be the vector from (x,y) to a.
        # Let v2A be the vector from a to b.
        # Find the angle alphaA between v1A and v2A.
        v1xA = x - a.point.x()
        v1yA = y - a.point.y()
        v2xA = b.point.x() - a.point.x()
        v2yA = b.point.y() - a.point.y()
        vpA = self.vprod(v1xA, v1yA, v2xA, v2yA)
        cosA = vpA / (self.vlen(v1xA, v1yA) * self.vlen(v2xA, v2yA))
        alphaA = acos(cosA)

        # Let v1B be the vector from x to b.
        # Let v2B be the vector from b to c.
        v1xB = x - b.point.x()
        v1yB = y - b.point.y()
        v2xB = c.point.x() - b.point.x()
        v2yB = c.point.y() - b.point.y()
        vpB = self.vprod(v1xB, v1yB, v2xB, v2yB)
        cosB = vpB / (self.vlen(v1xB, v1yB) * self.vlen(v2xB, v2yB))
        alphaB = acos(cosB)

        # Let v1C be the vector from x to c.
        # Let v2C be the vector from c back to a.
        v1xC = x - c.point.x()
        v1yC = y - c.point.y()
        v2xC = a.point.x() - c.point.x()
        v2yC = a.point.y() - c.point.y()
        vpC = self.vprod(v1xC, v1yC, v2xC, v2yC)
        cosC = vpC / (self.vlen(v1xC, v1yC) * self.vlen(v2xC, v2yC))
        alphaC = acos(cosC)

        # Find the radian angles between the (1,0) vector and the points
        # A, B, C and (x,y). Use this information to determine which of
        # the edges we should project (x,y) onto.
        angleA = self._angle_at(a.point, self.contentsRect())
        angleB = self._angle_at(b.point, self.contentsRect())
        angleC = self._angle_at(c.point, self.contentsRect())
        angleP = self._angle_at(QtCore.QPointF(x, y), self.contentsRect())

        # If (x,y) is in the a-b area, project onto the a-b vector.
        if self._angle_between_angles(angleP, angleA, angleB):
            # Find the distance from (x,y) to a. Then use the slope of
            # the a-b vector with this distance and the angle between a-b
            # and a-(x,y) to determine the point of intersection of the
            # perpendicular projection from (x,y) onto a-b.
            pdist = sqrt(
                ((x - a.point.x()) ** 2) + ((y - a.point.y()) ** 2)
            )

            # the length of all edges is always > 0
            p0x = (
                a.point.x()
                + ((b.point.x() - a.point.x()) / self.vlen(v2xB, v2yB))
                * cos(alphaA) * pdist
            )
            p0y = (
                a.point.y()
                + ((b.point.y() - a.point.y()) / self.vlen(v2xB, v2yB))
                * cos(alphaA) * pdist
            )

            # If (x,y) is above the a-b line, which basically means it's
            # outside the triangle, then return its projection onto a-b.
            if self._point_above_point(
                x, y,
                p0x, p0y,
                a.point.x(), a.point.y(),
                b.point.x(), b.point.y()
            ):
                # If the projection is "outside" a, return a. If it is
                # outside b, return b. Otherwise return the projection.
                n = self._point_in_line(
                    p0x, p0y,
                    a.point.x(), a.point.y(),
                    b.point.x(), b.point.y()
                )
                if n < 0:
                    return a.point
                elif n > 0:
                    return b.point

                return QtCore.QPointF(p0x, p0y)

        elif self._angle_between_angles(angleP, angleB, angleC):
            # If (x,y) is in the b-c area, project onto the b-c vector.
            pdist = sqrt(
                ((x - b.point.x()) ** 2) + ((y - b.point.y()) ** 2)
            )

            # the length of all edges is always > 0
            p0x = (
                b.point.x()
                + ((c.point.x() - b.point.x()) / self.vlen(v2xC, v2yC))
                * cos(alphaB) * pdist
            )
            p0y = (
                b.point.y()
                + ((c.point.y() - b.point.y()) / self.vlen(v2xC, v2yC))
                * cos(alphaB)
                * pdist
            )

            if self._point_above_point(
                x, y,
                p0x, p0y,
                b.point.x(), b.point.y(),
                c.point.x(), c.point.y()
            ):
                n = self._point_in_line(
                    p0x, p0y,
                    b.point.x(), b.point.y(),
                    c.point.x(), c.point.y()
                )
                if n < 0:
                    return b.point
                elif n > 0:
                    return c.point
                return QtCore.QPointF(p0x, p0y)

        elif self._angle_between_angles(angleP, angleC, angleA):
            # If (x,y) is in the c-a area, project onto the c-a vector.
            pdist = sqrt(
                ((x - c.point.x()) ** 2) + ((y - c.point.y()) ** 2)
            )

            # the length of all edges is always > 0
            p0x = (
                c.point.x()
                + ((a.point.x() - c.point.x()) / self.vlen(v2xA, v2yA))
                * cos(alphaC)
                * pdist
            )
            p0y = (
                c.point.y()
                + ((a.point.y() - c.point.y()) / self.vlen(v2xA, v2yA))
                * cos(alphaC) * pdist
            )

            if self._point_above_point(
                x, y,
                p0x, p0y,
                c.point.x(), c.point.y(),
                a.point.x(), a.point.y()
            ):
                n = self._point_in_line(
                    p0x, p0y,
                    c.point.x(), c.point.y(),
                    a.point.x(), a.point.y()
                )
                if n < 0:
                    return c.point
                elif n > 0:
                    return a.point
                return QtCore.QPointF(p0x, p0y)

        # (x,y) is inside the triangle (inside a-b, b-c and a-c).
        return QtCore.QPointF(x, y)
