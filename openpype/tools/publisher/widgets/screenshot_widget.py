import os
import tempfile

from qtpy import QtCore, QtGui, QtWidgets


class ScreenMarquee(QtWidgets.QDialog):
    """Dialog to interactively define screen area.

    This allows to select a screen area through a marquee selection.

    You can use any of its classmethods for easily saving an image,
    capturing to QClipboard or returning a QPixmap, respectively
    `capture_to_file`, `capture_to_clipboard` and `capture_to_pixmap`.
    """

    def __init__(self, parent=None):
        super(ScreenMarquee, self).__init__(parent=parent)

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
            | QtCore.Qt.CustomizeWindowHint
            | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setCursor(QtCore.Qt.CrossCursor)
        self.setMouseTracking(True)

        fade_anim = QtCore.QVariantAnimation()
        fade_anim.setStartValue(0)
        fade_anim.setEndValue(50)
        fade_anim.setDuration(200)
        fade_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        fade_anim.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

        fade_anim.valueChanged.connect(self._on_fade_anim)

        app = QtWidgets.QApplication.instance()
        if hasattr(app, "screenAdded"):
            app.screenAdded.connect(self._on_screen_added)
            app.screenRemoved.connect(self._fit_screen_geometry)
        elif hasattr(app, "desktop"):
            desktop = app.desktop()
            desktop.screenCountChanged.connect(self._fit_screen_geometry)

        for screen in QtWidgets.QApplication.screens():
            screen.geometryChanged.connect(self._fit_screen_geometry)

        self._opacity = fade_anim.currentValue()
        self._click_pos = None
        self._capture_rect = None

        self._fade_anim = fade_anim

    def get_captured_pixmap(self):
        if self._capture_rect is None:
            return QtGui.QPixmap()

        return self.get_desktop_pixmap(self._capture_rect)

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
            painter.setCompositionMode(
                QtGui.QPainter.CompositionMode_Clear)
            painter.drawRect(capture_rect)
            painter.setCompositionMode(
                QtGui.QPainter.CompositionMode_SourceOver)

        pen_color = QtGui.QColor(255, 255, 255, 64)
        pen = QtGui.QPen(pen_color, 1, QtCore.Qt.DotLine)
        painter.setPen(pen)

        # Draw cropping markers at click position
        rect = event.rect()
        if click_pos is not None:
            painter.drawLine(
                rect.left(), click_pos.y(),
                rect.right(), click_pos.y()
            )
            painter.drawLine(
                click_pos.x(), rect.top(),
                click_pos.x(), rect.bottom()
            )

        # Draw cropping markers at current mouse position
        painter.drawLine(
            rect.left(), mouse_pos.y(),
            rect.right(), mouse_pos.y()
        )
        painter.drawLine(
            mouse_pos.x(), rect.top(),
            mouse_pos.x(), rect.bottom()
        )

    def mousePressEvent(self, event):
        """Mouse click event"""

        if event.button() == QtCore.Qt.LeftButton:
            # Begin click drag operation
            self._click_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        """Mouse release event"""
        if (
            self._click_pos is not None
            and event.button() == QtCore.Qt.LeftButton
        ):
            # End click drag operation and commit the current capture rect
            self._capture_rect = QtCore.QRect(
                self._click_pos, event.globalPos()
            ).normalized()
            self._click_pos = None
        self.close()

    def mouseMoveEvent(self, event):
        """Mouse move event"""
        self.repaint()

    def keyPressEvent(self, event):
        """Mouse press event"""
        if event.button() == QtCore.Qt.Key_Escape:
            self._click_pos = None
            self._capture_rect = None
            self.close()
            return
        return super(ScreenMarquee, self).mousePressEvent(event)

    def showEvent(self, event):
        self._fit_screen_geometry()
        self._fade_anim.start()

    def _fit_screen_geometry(self):
        # Compute the union of all screen geometries, and resize to fit.
        workspace_rect = QtCore.QRect()
        for screen in QtWidgets.QApplication.screens():
            workspace_rect = workspace_rect.united(screen.geometry())
        self.setGeometry(workspace_rect)

    def _on_fade_anim(self):
        """Animation callback for opacity."""

        self._opacity = self._fade_anim.currentValue()
        self.repaint()

    def _on_screen_added(self):
        for screen in QtGui.QGuiApplication.screens():
            screen.geometryChanged.connect(self._fit_screen_geometry)

    @classmethod
    def get_desktop_pixmap(cls, rect):
        """Performs a screen capture on the specified rectangle.

        Args:
            rect (QtCore.QRect): The rectangle to capture.

        Returns:
            QtGui.QPixmap: Captured pixmap image
        """

        if rect.width() < 1 or rect.height() < 1:
            return QtGui.QPixmap()

        screen_pixes = []
        for screen in QtWidgets.QApplication.screens():
            screen_geo = screen.geometry()
            if not screen_geo.intersects(rect):
                continue

            screen_pix_rect = screen_geo.intersected(rect)
            screen_pix = screen.grabWindow(
                0,
                screen_pix_rect.x() - screen_geo.x(),
                screen_pix_rect.y() - screen_geo.y(),
                screen_pix_rect.width(), screen_pix_rect.height()
            )
            paste_point = QtCore.QPoint(
                screen_pix_rect.x() - rect.x(),
                screen_pix_rect.y() - rect.y()
            )
            screen_pixes.append((screen_pix, paste_point))

        output_pix = QtGui.QPixmap(rect.width(), rect.height())
        output_pix.fill(QtCore.Qt.transparent)
        pix_painter = QtGui.QPainter()
        pix_painter.begin(output_pix)
        for item in screen_pixes:
            (screen_pix, offset) = item
            pix_painter.drawPixmap(offset, screen_pix)

        pix_painter.end()

        return output_pix

    @classmethod
    def capture_to_pixmap(cls):
        """Take screenshot with marquee into pixmap.

        Note:
            The pixmap can be invalid (use 'isNull' to check).

        Returns:
            QtGui.QPixmap: Captured pixmap image.
        """

        tool = cls()
        tool.exec_()
        return tool.get_captured_pixmap()

    @classmethod
    def capture_to_file(cls, filepath=None):
        """Take screenshot with marquee into file.

        Args:
            filepath (Optional[str]): Path where screenshot will be saved.

        Returns:
            Union[str, None]: Path to the saved screenshot, or None if user
                cancelled the operation.
        """

        pixmap = cls.capture_to_pixmap()
        if pixmap.isNull():
            return None

        if filepath is None:
            with tempfile.NamedTemporaryFile(
                prefix="screenshot_", suffix=".png", delete=False
            ) as tmpfile:
                filepath = tmpfile.name

        else:
            output_dir = os.path.dirname(filepath)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

        pixmap.save(filepath)
        return filepath

    @classmethod
    def capture_to_clipboard(cls):
        """Take screenshot with marquee into clipboard.

        Notes:
            Screenshot is not in clipboard if user cancelled the operation.

        Returns:
            bool: Screenshot was added to clipboard.
        """

        clipboard = QtWidgets.QApplication.clipboard()
        pixmap = cls.capture_to_pixmap()
        if pixmap.isNull():
            return False
        image = pixmap.toImage()
        clipboard.setImage(image, QtGui.QClipboard.Clipboard)
        return True


def capture_to_pixmap():
    """Take screenshot with marquee into pixmap.

    Note:
        The pixmap can be invalid (use 'isNull' to check).

    Returns:
        QtGui.QPixmap: Captured pixmap image.
    """

    return ScreenMarquee.capture_to_pixmap()


def capture_to_file(filepath=None):
    """Take screenshot with marquee into file.

    Args:
        filepath (Optional[str]): Path where screenshot will be saved.

    Returns:
        Union[str, None]: Path to the saved screenshot, or None if user
            cancelled the operation.
    """

    return ScreenMarquee.capture_to_file(filepath)


def capture_to_clipboard():
    """Take screenshot with marquee into clipboard.

    Notes:
        Screenshot is not in clipboard if user cancelled the operation.

    Returns:
        bool: Screenshot was added to clipboard.
    """

    return ScreenMarquee.capture_to_clipboard()
