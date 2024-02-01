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
            QtCore.Qt.Window
            | QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
            | QtCore.Qt.CustomizeWindowHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setCursor(QtCore.Qt.CrossCursor)
        self.setMouseTracking(True)

        app = QtWidgets.QApplication.instance()
        if hasattr(app, "screenAdded"):
            app.screenAdded.connect(self._on_screen_added)
            app.screenRemoved.connect(self._fit_screen_geometry)
        elif hasattr(app, "desktop"):
            desktop = app.desktop()
            desktop.screenCountChanged.connect(self._fit_screen_geometry)

        for screen in QtWidgets.QApplication.screens():
            screen.geometryChanged.connect(self._fit_screen_geometry)

        self._opacity = 50
        self._click_pos = None
        self._capture_rect = None

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
        painter.setRenderHints(
            QtGui.QPainter.Antialiasing
            | QtGui.QPainter.SmoothPixmapTransform
        )

        # Draw background. Aside from aesthetics, this makes the full
        # tool region accept mouse events.
        painter.setBrush(QtGui.QColor(0, 0, 0, self._opacity))
        painter.setPen(QtCore.Qt.NoPen)
        rect = event.rect()
        fill_path = QtGui.QPainterPath()
        fill_path.addRect(rect)

        # Clear the capture area
        if click_pos is not None:
            sub_path = QtGui.QPainterPath()
            capture_rect = QtCore.QRect(click_pos, mouse_pos)
            sub_path.addRect(capture_rect)
            fill_path = fill_path.subtracted(sub_path)

        painter.drawPath(fill_path)

        pen_color = QtGui.QColor(255, 255, 255, self._opacity)
        pen = QtGui.QPen(pen_color, 1, QtCore.Qt.DotLine)
        painter.setPen(pen)

        # Draw cropping markers at click position
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
        painter.end()

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
        if event.key() == QtCore.Qt.Key_Escape:
            self._click_pos = None
            self._capture_rect = None
            event.accept()
            self.close()
            return
        return super(ScreenMarquee, self).keyPressEvent(event)

    def showEvent(self, event):
        self._fit_screen_geometry()

    def _fit_screen_geometry(self):
        # Compute the union of all screen geometries, and resize to fit.
        workspace_rect = QtCore.QRect()
        for screen in QtWidgets.QApplication.screens():
            workspace_rect = workspace_rect.united(screen.geometry())
        self.setGeometry(workspace_rect)

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
        # Activate so Escape event is not ignored.
        tool.setWindowState(QtCore.Qt.WindowActive)
        # Exec dialog and return captured pixmap.
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
