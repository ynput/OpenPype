import uuid

from Qt import QtWidgets, QtCore, QtGui

from .lib import set_style_property


class CloseButton(QtWidgets.QFrame):
    """Close button drawed manually."""

    clicked = QtCore.Signal()

    def __init__(self, parent):
        super(CloseButton, self).__init__(parent)
        self._mouse_pressed = False
        policy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.Fixed
        )
        self.setSizePolicy(policy)

    def sizeHint(self):
        size = self.fontMetrics().height()
        return QtCore.QSize(size, size)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._mouse_pressed = True
        super(CloseButton, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._mouse_pressed:
            self._mouse_pressed = False
            if self.rect().contains(event.pos()):
                self.clicked.emit()

        super(CloseButton, self).mouseReleaseEvent(event)

    def paintEvent(self, event):
        rect = self.rect()
        painter = QtGui.QPainter(self)
        painter.setClipRect(event.rect())
        pen = QtGui.QPen()
        pen.setWidth(2)
        pen.setColor(QtGui.QColor(255, 255, 255))
        pen.setStyle(QtCore.Qt.SolidLine)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        offset = int(rect.height() / 4)
        top = rect.top() + offset
        left = rect.left() + offset
        right = rect.right() - offset
        bottom = rect.bottom() - offset
        painter.drawLine(
            left, top,
            right, bottom
        )
        painter.drawLine(
            left, bottom,
            right, top
        )


class MessageWidget(QtWidgets.QFrame):
    """Message widget showed as overlay.

    Message is hidden after timeout but can be overriden by mouse hover.
    Mouse hover can add additional 2 seconds of widget's visibility.

    Args:
        message_id (str): Unique identifier of message widget for
            'MessageOverlayObject'.
        message (str): Text shown in message.
        parent (QWidget): Parent widget where message is visible.
        timeout (int): Timeout of message's visibility (default 5000).
        message_type (str): Property which can be used in styles for specific
            kid of message.
    """

    close_requested = QtCore.Signal(str)
    _default_timeout = 5000

    def __init__(
        self, message_id, message, parent, timeout=None, message_type=None
    ):
        super(MessageWidget, self).__init__(parent)
        self.setObjectName("OverlayMessageWidget")

        if message_type:
            set_style_property(self, "type", message_type)

        if not timeout:
            timeout = self._default_timeout
        timeout_timer = QtCore.QTimer()
        timeout_timer.setInterval(timeout)
        timeout_timer.setSingleShot(True)

        hover_timer = QtCore.QTimer()
        hover_timer.setInterval(2000)
        hover_timer.setSingleShot(True)

        label_widget = QtWidgets.QLabel(message, self)
        label_widget.setAlignment(QtCore.Qt.AlignCenter)
        label_widget.setWordWrap(True)
        close_btn = CloseButton(self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 0, 5)
        layout.addWidget(label_widget, 1)
        layout.addWidget(close_btn, 0)

        close_btn.clicked.connect(self._on_close_clicked)
        timeout_timer.timeout.connect(self._on_timer_timeout)
        hover_timer.timeout.connect(self._on_hover_timeout)

        self._label_widget = label_widget
        self._message_id = message_id
        self._timeout_timer = timeout_timer
        self._hover_timer = hover_timer

    def size_hint_without_word_wrap(self):
        """Size hint in cases that word wrap of label is disabled."""
        self._label_widget.setWordWrap(False)
        size_hint = self.sizeHint()
        self._label_widget.setWordWrap(True)
        return size_hint

    def showEvent(self, event):
        """Start timeout on show."""
        super(MessageWidget, self).showEvent(event)
        self._timeout_timer.start()

    def _on_timer_timeout(self):
        """On message timeout."""
        # Skip closing if hover timer is active
        if not self._hover_timer.isActive():
            self._close_message()

    def _on_hover_timeout(self):
        """Hover timer timed out."""
        # Check if is still under widget
        if self.underMouse():
            self._hover_timer.start()
        else:
            self._close_message()

    def _on_close_clicked(self):
        self._close_message()

    def _close_message(self):
        """Emmit close request to 'MessageOverlayObject'."""
        self.close_requested.emit(self._message_id)

    def enterEvent(self, event):
        """Start hover timer on hover."""
        super(MessageWidget, self).enterEvent(event)
        self._hover_timer.start()

    def leaveEvent(self, event):
        """Start hover timer on hover leave."""
        super(MessageWidget, self).leaveEvent(event)
        self._hover_timer.start()


class MessageOverlayObject(QtCore.QObject):
    """Object that can be used to add overlay messages.

    Args:
        widget (QWidget):
    """

    def __init__(self, widget):
        super(MessageOverlayObject, self).__init__()

        widget.installEventFilter(self)

        # Timer which triggers recalculation of message positions
        recalculate_timer = QtCore.QTimer()
        recalculate_timer.setInterval(10)

        recalculate_timer.timeout.connect(self._recalculate_positions)

        self._widget = widget
        self._recalculate_timer = recalculate_timer

        self._messages_order = []
        self._closing_messages = set()
        self._messages = {}
        self._spacing = 5
        self._move_size = 4
        self._move_size_remove = 8

    def add_message(self, message, timeout=None, message_type=None):
        """Add single message into overlay.

        Args:
            message (str): Message that will be shown.
            timeout (int): Message timeout.
            message_type (str): Message type can be used as property in
                stylesheets.
        """
        # Skip empty messages
        if not message:
            return

        # Create unique id of message
        label_id = str(uuid.uuid4())
        # Create message widget
        widget = MessageWidget(
            label_id, message, self._widget, timeout, message_type
        )
        widget.close_requested.connect(self._on_message_close_request)
        widget.show()

        # Move widget outside of window
        pos = widget.pos()
        pos.setY(pos.y() - widget.height())
        widget.move(pos)
        # Store message
        self._messages[label_id] = widget
        self._messages_order.append(label_id)
        # Trigger recalculation timer
        self._recalculate_timer.start()

    def _on_message_close_request(self, label_id):
        """Message widget requested removement."""

        widget = self._messages.get(label_id)
        if widget is not None:
            # Add message to closing messages and start recalculation
            self._closing_messages.add(label_id)
            self._recalculate_timer.start()

    def _recalculate_positions(self):
        """Recalculate positions of widgets."""

        # Skip if there are no messages to process
        if not self._messages_order:
            self._recalculate_timer.stop()
            return

        # All message widgets are in expected positions
        all_at_place = True
        # Starting y position
        pos_y = self._spacing
        # Current widget width
        widget_width = self._widget.width()
        max_width = widget_width - (2 * self._spacing)
        widget_half_width = widget_width / 2

        # Store message ids that should be removed
        message_ids_to_remove = set()
        for message_id in reversed(self._messages_order):
            widget = self._messages[message_id]
            pos = widget.pos()
            # Messages to remove are moved upwards
            if message_id in self._closing_messages:
                bottom = pos.y() + widget.height()
                # Add message to remove if is not visible
                if bottom < 0 or self._move_size_remove < 1:
                    message_ids_to_remove.add(message_id)
                    continue

                # Calculate new y position of message
                dst_pos_y = pos.y() - self._move_size_remove

            else:
                # Calculate y position of message
                # - use y position of previous message widget and add
                #   move size if is not in final destination yet
                if widget.underMouse():
                    dst_pos_y = pos.y()
                elif pos.y() == pos_y or self._move_size < 1:
                    dst_pos_y = pos_y
                elif pos.y() < pos_y:
                    dst_pos_y = min(pos_y, pos.y() + self._move_size)
                else:
                    dst_pos_y = max(pos_y, pos.y() - self._move_size)

            # Store if widget is in place where should be
            if all_at_place and dst_pos_y != pos_y:
                all_at_place = False

            # Calculate ideal width and height of message widget
            height = widget.heightForWidth(max_width)
            w_size_hint = widget.size_hint_without_word_wrap()
            widget.resize(min(max_width, w_size_hint.width()), height)

            # Center message widget
            size = widget.size()
            pos_x = widget_half_width - (size.width() / 2)
            # Move widget to destination position
            widget.move(pos_x, dst_pos_y)

            # Add message widget height and spacing for next message widget
            pos_y += size.height() + self._spacing

        # Remove widgets to remove
        for message_id in message_ids_to_remove:
            self._messages_order.remove(message_id)
            self._closing_messages.remove(message_id)
            widget = self._messages.pop(message_id)
            widget.hide()
            widget.deleteLater()

        # Stop recalculation timer if all widgets are where should be
        if all_at_place:
            self._recalculate_timer.stop()

    def eventFilter(self, source, event):
        # Trigger recalculation of timer on resize of widget
        if source is self._widget and event.type() == QtCore.QEvent.Resize:
            self._recalculate_timer.start()

        return super(MessageOverlayObject, self).eventFilter(source, event)
