import Qt
from Qt import QtCore, QtGui
from . import screen_grab

class Thumbnail(QtGui.QLabel):
    """
    A specialized, custom widget that either displays a
    static square thumbnail or a thumbnail that can be captured
    using screen capture and other methods.
    """

    # emitted when screen is captured
    # passes the QPixmap as a parameter
    screen_grabbed = QtCore.Signal(object)

    # internal signal to initiate screengrab
    _do_screengrab = QtCore.Signal()

    def __init__(self, parent=None):
        """
        :param parent: The parent QWidget for this control
        """
        QtGui.QLabel.__init__(self, parent)

        # _multiple_values allows to display indicator that the summary thumbnail is not applied to all items
        self._multiple_values = False

        self._thumbnail = None
        self._enabled = True
        self.setAutoFillBackground(True)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self._no_thumb_pixmap = QtGui.QPixmap(":/tk_multi_publish2/camera.png")
        self._do_screengrab.connect(self._on_screengrab)
        self.set_thumbnail(self._no_thumb_pixmap)

    def setEnabled(self, enabled):
        """
        Overrides base class setEnabled
        :param bool enabled: flag to indicate enabled state of the widget
        """
        self._enabled = enabled
        if enabled:
            self.setCursor(QtCore.Qt.PointingHandCursor)
        else:
            self.unsetCursor()

    def set_thumbnail(self, pixmap):
        """
        Set pixmap to be displayed
        :param pixmap: QPixmap to show or None in order to show default one.
        """
        if pixmap is None:
            self._set_screenshot_pixmap(self._no_thumb_pixmap)
        else:
            self._set_screenshot_pixmap(pixmap)

    def mousePressEvent(self, event):
        """
        Fires when the mouse is pressed.
        In order to emulate the aesthetics of a button,
        a white frame is rendered around the label at mouse press.
        """
        QtGui.QLabel.mousePressEvent(self, event)

        if self._enabled:
            self.setStyleSheet("QLabel {border: 1px solid #eee;}")

    def mouseReleaseEvent(self, event):
        """
        Fires when the mouse is released
        Stops drawing the border and emits an internal
        screen grab signal.
        """
        QtGui.QLabel.mouseReleaseEvent(self, event)

        if self._enabled:
            # disable style
            self.setStyleSheet(None)

            # if the mouse is released over the widget,
            # kick off the screengrab
            pos_mouse = event.pos()
            if self.rect().contains(pos_mouse):
                self._do_screengrab.emit()

    def _on_screengrab(self):
        """
        Perform a screengrab and update the label pixmap.
        Emit screen_grabbed signal.
        """

        self.window().hide()
        try:
            pixmap = screen_grab.ScreenGrabber.screen_capture()
        finally:
            self.window().show()

        if pixmap:

            self._multiple_values = False
            self._set_screenshot_pixmap(pixmap)
            self.screen_grabbed.emit(pixmap)

    def _set_multiple_values_indicator(self, is_multiple_values):
        """
        Specifies wether to show multiple values indicator
        """
        self._multiple_values = is_multiple_values

    def paintEvent(self, paint_event):
        """
        Paint Event override
        """
        # paint multiple values indicator
        if self._multiple_values == True:
            p = QtGui.QPainter(self)
            p.drawPixmap(
                0,
                0,
                self.width(),
                self.height(),
                self._no_thumb_pixmap,
                0,
                0,
                self._no_thumb_pixmap.width(),
                self._no_thumb_pixmap.height(),
            )
            p.fillRect(0, 0, self.width(), self.height(), QtGui.QColor(42, 42, 42, 237))
            p.setFont(QtGui.QFont("Arial", 15, QtGui.QFont.Bold))
            pen = QtGui.QPen(QtGui.QColor("#18A7E3"))
            p.setPen(pen)
            p.drawText(self.rect(), QtCore.Qt.AlignCenter, "Multiple Values")

        else:
            # paint thumbnail
            QtGui.QLabel.paintEvent(self, paint_event)

    def _set_screenshot_pixmap(self, pixmap):
        """
        Takes the given QPixmap and sets it to be the thumbnail
        image of the note input widget.
        :param pixmap:  A QPixmap object containing the screenshot image.
        """
        self._thumbnail = pixmap

        # format it to fit the label size
        thumb = self._thumbnail.scaled(
            self.width(),
            self.height(),
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )

        self.setPixmap(thumb)