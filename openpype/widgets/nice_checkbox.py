from math import floor, sqrt, ceil
from Qt import QtWidgets, QtCore, QtGui

from openpype.style import get_objected_colors


class NiceCheckbox(QtWidgets.QFrame):
    stateChanged = QtCore.Signal(int)
    clicked = QtCore.Signal()

    _checked_bg_color = None
    _unchecked_bg_color = None
    _checker_color = None
    _checker_hover_color = None

    def __init__(self, checked=False, draw_icons=False, parent=None):
        super(NiceCheckbox, self).__init__(parent)

        self.setObjectName("NiceCheckbox")
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.Fixed
        )
        self._checked = checked
        if checked:
            checkstate = QtCore.Qt.Checked
        else:
            checkstate = QtCore.Qt.Unchecked
        self._checkstate = checkstate
        self._is_tristate = False

        self._draw_icons = draw_icons

        self._animation_timer = QtCore.QTimer(self)
        self._animation_timeout = 6

        self._fixed_width_set = False
        self._fixed_height_set = False

        self._current_step = None
        self._steps = 21
        self._middle_step = 11
        self.set_steps(self._steps)

        self._checker_margins_divider = 0

        self._pressed = False
        self._under_mouse = False

        self.icon_scale_factor = sqrt(2) / 2

        icon_path_stroker = QtGui.QPainterPathStroker()
        icon_path_stroker.setCapStyle(QtCore.Qt.RoundCap)
        icon_path_stroker.setJoinStyle(QtCore.Qt.RoundJoin)

        self.icon_path_stroker = icon_path_stroker

        self._animation_timer.timeout.connect(self._on_animation_timeout)

        self._base_size = QtCore.QSize(90, 50)
        self._load_colors()

    @classmethod
    def _load_colors(cls):
        if cls._checked_bg_color is not None:
            return

        colors_data = get_objected_colors()
        colors_info = colors_data["nice-checkbox"]

        cls._checked_bg_color = colors_info["bg-checked"].get_qcolor()
        cls._unchecked_bg_color = colors_info["bg-unchecked"].get_qcolor()

        cls._checker_color = colors_info["bg-checker"].get_qcolor()
        cls._checker_hover_color = colors_info["bg-checker-hover"].get_qcolor()

    @property
    def checked_bg_color(self):
        return self._checked_bg_color

    @property
    def unchecked_bg_color(self):
        return self._unchecked_bg_color

    @property
    def checker_color(self):
        return self._checker_color

    @property
    def checker_hover_color(self):
        return self._checker_hover_color

    def setTristate(self, tristate=True):
        if self._is_tristate != tristate:
            self._is_tristate = tristate

    def set_draw_icons(self, draw_icons=None):
        if draw_icons is None:
            draw_icons = not self._draw_icons

        if draw_icons == self._draw_icons:
            return

        self._draw_icons = draw_icons
        self.repaint()

    def sizeHint(self):
        height = self.fontMetrics().height()
        width = self.get_width_hint_by_height(height)
        return QtCore.QSize(width, height)

    def get_width_hint_by_height(self, height):
        return (
            height / self._base_size.height()
        ) * self._base_size.width()

    def get_height_hint_by_width(self, width):
        return (
            width / self._base_size.width()
        ) * self._base_size.height()

    def setFixedHeight(self, *args, **kwargs):
        self._fixed_height_set = True
        super(NiceCheckbox, self).setFixedHeight(*args, **kwargs)
        if not self._fixed_width_set:
            width = self.get_width_hint_by_height(self.height())
            self.setFixedWidth(width)

    def setFixedWidth(self, *args, **kwargs):
        self._fixed_width_set = True
        super(NiceCheckbox, self).setFixedWidth(*args, **kwargs)
        if not self._fixed_height_set:
            height = self.get_height_hint_by_width(self.width())
            self.setFixedHeight(height)

    def setFixedSize(self, *args, **kwargs):
        self._fixed_height_set = True
        self._fixed_width_set = True
        super(NiceCheckbox, self).setFixedSize(*args, **kwargs)

    def steps(self):
        return self._steps

    def set_steps(self, steps):
        if steps < 2:
            steps = 2

        # Make sure animation is stopped
        if self._animation_timer.isActive():
            self._animation_timer.stop()

        # Set steps and set current step by current checkstate
        self._steps = steps
        diff = steps % 2
        self._middle_step = (int(steps - diff) / 2) + diff
        if self._checkstate == QtCore.Qt.Checked:
            self._current_step = self._steps
        elif self._checkstate == QtCore.Qt.Unchecked:
            self._current_step = 0
        else:
            self._current_step = self._middle_step

    def checkState(self):
        return self._checkstate

    def isChecked(self):
        return self._checked

    def setCheckState(self, state):
        if self._checkstate == state:
            return

        self._checkstate = state
        if state == QtCore.Qt.Checked:
            self._checked = True
        elif state == QtCore.Qt.Unchecked:
            self._checked = False

        self.stateChanged.emit(self.checkState())

        if self._animation_timer.isActive():
            self._animation_timer.stop()

        if self.isVisible() and self.isEnabled():
            # Start animation
            self._animation_timer.start(self._animation_timeout)
        else:
            # Do not animate change if is disabled
            if state == QtCore.Qt.Checked:
                self._current_step = self._steps
            elif state == QtCore.Qt.Unchecked:
                self._current_step = 0
            else:
                self._current_step = self._middle_step
            self.repaint()

    def setChecked(self, checked):
        if checked == self._checked:
            return

        if checked:
            checkstate = QtCore.Qt.Checked
        else:
            checkstate = QtCore.Qt.Unchecked

        self.setCheckState(checkstate)

    def nextCheckState(self):
        if self._checkstate == QtCore.Qt.Unchecked:
            if self._is_tristate:
                return QtCore.Qt.PartiallyChecked
            return QtCore.Qt.Checked

        if self._checkstate == QtCore.Qt.Checked:
            return QtCore.Qt.Unchecked

        if self._checked:
            return QtCore.Qt.Unchecked
        return QtCore.Qt.Checked

    def mousePressEvent(self, event):
        if event.buttons() & QtCore.Qt.LeftButton:
            self._pressed = True
            self.repaint()
        super(NiceCheckbox, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._pressed and not event.buttons() & QtCore.Qt.LeftButton:
            self._pressed = False
            if self.rect().contains(event.pos()):
                self.setCheckState(self.nextCheckState())
                self.clicked.emit()
                event.accept()
                return
        super(NiceCheckbox, self).mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self._pressed:
            under_mouse = self.rect().contains(event.pos())
            if under_mouse != self._under_mouse:
                self._under_mouse = under_mouse
                self.repaint()

        super(NiceCheckbox, self).mouseMoveEvent(event)

    def enterEvent(self, event):
        self._under_mouse = True
        if self.isEnabled():
            self.repaint()
        super(NiceCheckbox, self).enterEvent(event)

    def leaveEvent(self, event):
        self._under_mouse = False
        if self.isEnabled():
            self.repaint()
        super(NiceCheckbox, self).leaveEvent(event)

    def _on_animation_timeout(self):
        if self._checkstate == QtCore.Qt.Checked:
            if self._current_step == self._steps:
                self._animation_timer.stop()
                return
            self._current_step += 1

        elif self._checkstate == QtCore.Qt.Unchecked:
            if self._current_step == 0:
                self._animation_timer.stop()
                return
            self._current_step -= 1

        else:
            if self._current_step < self._middle_step:
                self._current_step += 1

            elif self._current_step > self._middle_step:
                self._current_step -= 1

            if self._current_step == self._middle_step:
                self._animation_timer.stop()

        self.repaint()

    @staticmethod
    def steped_color(color1, color2, offset_ratio):
        red_dif = (
            color1.red() - color2.red()
        )
        green_dif = (
            color1.green() - color2.green()
        )
        blue_dif = (
            color1.blue() - color2.blue()
        )
        red = int(color2.red() + (
            red_dif * offset_ratio
        ))
        green = int(color2.green() + (
            green_dif * offset_ratio
        ))
        blue = int(color2.blue() + (
            blue_dif * offset_ratio
        ))

        return QtGui.QColor(red, green, blue)

    def paintEvent(self, event):
        frame_rect = QtCore.QRect(self.rect())
        if frame_rect.width() < 0 or frame_rect.height() < 0:
            return

        painter = QtGui.QPainter(self)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Draw inner background
        if self._current_step == self._steps:
            bg_color = self.checked_bg_color

        elif self._current_step == 0:
            bg_color = self.unchecked_bg_color

        else:
            offset_ratio = self._current_step / self._steps
            # Animation bg
            bg_color = self.steped_color(
                self.checked_bg_color,
                self.unchecked_bg_color,
                offset_ratio
            )

        margins_ratio = self._checker_margins_divider
        if margins_ratio > 0:
            size_without_margins = int(
                (frame_rect.height() / margins_ratio) * (margins_ratio - 2)
            )
            size_without_margins -= size_without_margins % 2
            margin_size_c = ceil(
                frame_rect.height() - size_without_margins
            ) / 2

        else:
            size_without_margins = frame_rect.height()
            margin_size_c = 0

        checkbox_rect = QtCore.QRect(
            frame_rect.x() + margin_size_c,
            frame_rect.y() + margin_size_c,
            frame_rect.width() - (margin_size_c * 2),
            frame_rect.height() - (margin_size_c * 2)
        )

        if checkbox_rect.width() > checkbox_rect.height():
            radius = floor(checkbox_rect.height() / 2)
        else:
            radius = floor(checkbox_rect.width() / 2)

        painter.setPen(QtCore.Qt.transparent)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(checkbox_rect, radius, radius)

        # Draw checker
        checker_size = size_without_margins - (margin_size_c * 2)
        area_width = (
            checkbox_rect.width()
            - (margin_size_c * 2)
            - checker_size
        )
        if self._current_step == 0:
            x_offset = 0
        else:
            x_offset = (area_width / self._steps) * self._current_step

        pos_x = checkbox_rect.x() + x_offset + margin_size_c
        pos_y = checkbox_rect.y() + margin_size_c

        checker_rect = QtCore.QRect(pos_x, pos_y, checker_size, checker_size)

        under_mouse = self.isEnabled() and self._under_mouse
        if under_mouse:
            checker_color = self.checker_hover_color
        else:
            checker_color = self.checker_color

        painter.setBrush(checker_color)
        painter.drawEllipse(checker_rect)

        if self._draw_icons:
            painter.setBrush(bg_color)
            icon_path = self._get_icon_path(painter, checker_rect)
            painter.drawPath(icon_path)

        # Draw shadow overlay
        if not self.isEnabled():
            level = 33
            alpha = 127
            painter.setPen(QtCore.Qt.transparent)
            painter.setBrush(QtGui.QColor(level, level, level, alpha))
            painter.drawRoundedRect(checkbox_rect, radius, radius)

        painter.end()

    def _get_icon_path(self, painter, checker_rect):
        self.icon_path_stroker.setWidth(checker_rect.height() / 5)

        if self._current_step == self._steps:
            return self._get_enabled_icon_path(painter, checker_rect)

        if self._current_step == 0:
            return self._get_disabled_icon_path(painter, checker_rect)

        if self._current_step == self._middle_step:
            return self._get_middle_circle_path(painter, checker_rect)

        disabled_step = self._steps - self._current_step
        enabled_step = self._steps - disabled_step
        half_steps = self._steps + 1 - ((self._steps + 1) % 2)
        if enabled_step > disabled_step:
            return self._get_enabled_icon_path(
                painter, checker_rect, enabled_step, half_steps
            )
        else:
            return self._get_disabled_icon_path(
                painter, checker_rect, disabled_step, half_steps
            )

    def _get_middle_circle_path(self, painter, checker_rect):
        width = self.icon_path_stroker.width()
        path = QtGui.QPainterPath()
        path.addEllipse(checker_rect.center(), width, width)

        return path

    def _get_enabled_icon_path(
        self, painter, checker_rect, step=None, half_steps=None
    ):
        fifteenth = checker_rect.height() / 15
        # Left point
        p1 = QtCore.QPoint(
            checker_rect.x() + (5 * fifteenth),
            checker_rect.y() + (9 * fifteenth)
        )
        # Middle bottom point
        p2 = QtCore.QPoint(
            checker_rect.center().x(),
            checker_rect.y() + (11 * fifteenth)
        )
        # Top right point
        p3 = QtCore.QPoint(
            checker_rect.x() + (10 * fifteenth),
            checker_rect.y() + (5 * fifteenth)
        )
        if step is not None:
            multiplier = (half_steps - step)

            p1c = p1 - checker_rect.center()
            p2c = p2 - checker_rect.center()
            p3c = p3 - checker_rect.center()

            p1o = QtCore.QPoint(
                (p1c.x() / half_steps) * multiplier,
                (p1c.y() / half_steps) * multiplier
            )
            p2o = QtCore.QPoint(
                (p2c.x() / half_steps) * multiplier,
                (p2c.y() / half_steps) * multiplier
            )
            p3o = QtCore.QPoint(
                (p3c.x() / half_steps) * multiplier,
                (p3c.y() / half_steps) * multiplier
            )

            p1 -= p1o
            p2 -= p2o
            p3 -= p3o

        path = QtGui.QPainterPath(p1)
        path.lineTo(p2)
        path.lineTo(p3)

        return self.icon_path_stroker.createStroke(path)

    def _get_disabled_icon_path(
        self, painter, checker_rect, step=None, half_steps=None
    ):
        center_point = QtCore.QPointF(
            checker_rect.width() / 2, checker_rect.height() / 2
        )
        offset = (
            (center_point + QtCore.QPointF(0, 0)) / 2
        ).x() / 4 * 5
        if step is not None:
            diff = center_point.x() - offset
            diff_offset = (diff / half_steps) * (half_steps - step)
            offset += diff_offset

        line1_p1 = QtCore.QPointF(
            checker_rect.topLeft().x() + offset,
            checker_rect.topLeft().y() + offset,
        )
        line1_p2 = QtCore.QPointF(
            checker_rect.bottomRight().x() - offset,
            checker_rect.bottomRight().y() - offset
        )
        line2_p1 = QtCore.QPointF(
            checker_rect.bottomLeft().x() + offset,
            checker_rect.bottomLeft().y() - offset
        )
        line2_p2 = QtCore.QPointF(
            checker_rect.topRight().x() - offset,
            checker_rect.topRight().y() + offset
        )
        path = QtGui.QPainterPath()
        path.moveTo(line1_p1)
        path.lineTo(line1_p2)
        path.moveTo(line2_p1)
        path.lineTo(line2_p2)

        return self.icon_path_stroker.createStroke(path)
