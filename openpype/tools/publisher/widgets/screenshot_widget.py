import tempfile
import sys
import os

from qtpy import QtCore, QtGui, QtWidgets


class ScreenMarquee(QtWidgets.QDialog):
    """Dialog to interactively define screen area.

    This allows to select a screen area through a marquee selection.

    You can use any of its classmethods for easily saving an image,
    capturing to QClipboard or returning a QPixmap, respectively
    `capture_file`, `capture_clipboard` and `capture_pixmap`.

    """

    def __init__(self, parent=None):
        """Constructor"""
        super(ScreenMarquee, self).__init__(parent=parent)

        self._opacity = 1
        self._click_pos = None
        self._capture_rect = QtCore.QRect()

        self.setWindowFlags(QtCore.Qt.FramelessWindowHint |
                            QtCore.Qt.WindowStaysOnTopHint |
                            QtCore.Qt.CustomizeWindowHint |
                            QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setCursor(QtCore.Qt.CrossCursor)
        self.setMouseTracking(True)

        desktop = QtWidgets.QApplication.desktop()
        desktop.resized.connect(self._fit_screen_geometry)
        desktop.screenCountChanged.connect(self._fit_screen_geometry)

    @property
    def capture_rect(self):
        """The resulting QRect from a previous capture operation."""
        return self._capture_rect

    def paintEvent(self, event):
        """Paint event"""

        # Convert click and current mouse positions to local space.
        mouse_pos = self.mapFromGlobal(QtGui.QCursor.pos())
        click_pos = None
        if self._click_pos is not None:
            click_pos = self.mapFromGlobal(self._click_pos)

        painter = QtGui.QPainter(self)

        # Draw background. Aside from aesthetics, this makes the full
        # tool region accept mouse events.
        painter.setBrush(QtGui.QColor(0, 0, 0, self._opacity))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(event.rect())

        # Clear the capture area
        if click_pos is not None:
            capture_rect = QtCore.QRect(click_pos, mouse_pos)
            painter.setCompositionMode(painter.CompositionMode_Clear)
            painter.drawRect(capture_rect)
            painter.setCompositionMode(painter.CompositionMode_SourceOver)

        pen_color = QtGui.QColor(255, 255, 255, 64)
        pen = QtGui.QPen(pen_color, 1, QtCore.Qt.DotLine)
        painter.setPen(pen)

        # Draw cropping markers at click position
        rect = event.rect()
        if click_pos is not None:
            painter.drawLine(rect.left(), click_pos.y(),
                             rect.right(), click_pos.y())
            painter.drawLine(click_pos.x(), rect.top(),
                             click_pos.x(), rect.bottom())

        # Draw cropping markers at current mouse position
        painter.drawLine(rect.left(), mouse_pos.y(),
                         rect.right(), mouse_pos.y())
        painter.drawLine(mouse_pos.x(), rect.top(),
                         mouse_pos.x(), rect.bottom())

    def mousePressEvent(self, event):
        """Mouse click event"""

        if event.button() == QtCore.Qt.LeftButton:
            # Begin click drag operation
            self._click_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        """Mouse release event"""
        if event.button() == QtCore.Qt.LeftButton and self._click_pos is not None:
            # End click drag operation and commit the current capture rect
            self._capture_rect = QtCore.QRect(self._click_pos,
                                              event.globalPos()).normalized()
            self._click_pos = None
        self.close()

    def mouseMoveEvent(self, event):
        """Mouse move event"""
        self.repaint()

    @classmethod
    def capture_pixmap(cls):
        """Modally capture screen with marquee into pixmap.

        Returns:
            QtGui.QPixmap: Captured pixmap image
        """

        tool = cls()
        tool.exec_()
        return get_desktop_pixmap(tool.capture_rect)

    @classmethod
    def capture_file(cls, filepath=None):

        if filepath is None:
            filepath = tempfile.NamedTemporaryFile(prefix="screenshot_",
                                                   suffix=".png",
                                                   delete=False).name
        pixmap = cls.capture_pixmap()
        pixmap.save(filepath)
        return filepath

    @classmethod
    def capture_clipboard(cls):
        clipboard = QtWidgets.QApplication.clipboard()
        pixmap = cls.capture_pixmap()
        image = pixmap.toImage()
        clipboard.setImage(image, QtGui.QClipboard.Clipboard);

    def showEvent(self, event):
        """
        Show event
        """
        self._fit_screen_geometry()

        # Start fade in animation
        fade_anim = QtCore.QPropertyAnimation(self, b"_opacity_anim_prop", self)
        fade_anim.setStartValue(self._opacity)
        fade_anim.setEndValue(50)
        fade_anim.setDuration(200)
        fade_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        fade_anim.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

    def _set_opacity(self, value):
        """
        Animation callback for opacity
        """
        self._opacity = value
        self.repaint()

    def _get_opacity(self):
        """
        Animation callback for opacity
        """
        return self._opacity

    _opacity_anim_prop = QtCore.Property(int, _get_opacity, _set_opacity)

    def _fit_screen_geometry(self):
        # Compute the union of all screen geometries, and resize to fit.
        screens = QtGui.QGuiApplication.screens()
        workspace_rect = QtCore.QRect()
        for screen in screens:
            workspace_rect = workspace_rect.united(screen.geometry())
        self.setGeometry(workspace_rect)


def get_desktop_pixmap(rect):
    """Performs a screen capture on the specified rectangle.

    Args:
        rect (QtCore.QRect): The rectangle to capture.

    Returns:
        QtGui.QPixmap: Captured pixmap image

    """
    desktop = QtWidgets.QApplication.desktop()
    pixmap = QtGui.QPixmap.grabWindow(desktop.winId(),
                                      rect.x(),
                                      rect.y(),
                                      rect.width(),
                                      rect.height())

    return pixmap

ScreenMarquee.capture_clipboard()
