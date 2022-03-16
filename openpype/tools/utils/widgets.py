import logging

from Qt import QtWidgets, QtCore, QtGui
import qargparse
import qtawesome
from openpype.style import (
    get_objected_colors,
    get_style_image_path
)

log = logging.getLogger(__name__)


class PlaceholderLineEdit(QtWidgets.QLineEdit):
    """Set placeholder color of QLineEdit in Qt 5.12 and higher."""
    def __init__(self, *args, **kwargs):
        super(PlaceholderLineEdit, self).__init__(*args, **kwargs)
        # Change placeholder palette color
        if hasattr(QtGui.QPalette, "PlaceholderText"):
            filter_palette = self.palette()
            color_obj = get_objected_colors()["font"]
            color = color_obj.get_qcolor()
            color.setAlpha(67)
            filter_palette.setColor(
                QtGui.QPalette.PlaceholderText,
                color
            )
            self.setPalette(filter_palette)


class BaseClickableFrame(QtWidgets.QFrame):
    """Widget that catch left mouse click and can trigger a callback.

    Callback is defined by overriding `_mouse_release_callback`.
    """
    def __init__(self, parent):
        super(BaseClickableFrame, self).__init__(parent)

        self._mouse_pressed = False

    def _mouse_release_callback(self):
        pass

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._mouse_pressed = True
        super(BaseClickableFrame, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._mouse_pressed:
            self._mouse_pressed = False
            if self.rect().contains(event.pos()):
                self._mouse_release_callback()

        super(BaseClickableFrame, self).mouseReleaseEvent(event)


class ClickableFrame(BaseClickableFrame):
    """Extended clickable frame which triggers 'clicked' signal."""
    clicked = QtCore.Signal()

    def _mouse_release_callback(self):
        self.clicked.emit()


class ClickableLabel(QtWidgets.QLabel):
    """Label that catch left mouse click and can trigger 'clicked' signal."""
    clicked = QtCore.Signal()

    def __init__(self, parent):
        super(ClickableLabel, self).__init__(parent)

        self._mouse_pressed = False

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._mouse_pressed = True
        super(ClickableLabel, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._mouse_pressed:
            self._mouse_pressed = False
            if self.rect().contains(event.pos()):
                self.clicked.emit()

        super(ClickableLabel, self).mouseReleaseEvent(event)


class ExpandBtnLabel(QtWidgets.QLabel):
    """Label showing expand icon meant for ExpandBtn."""
    def __init__(self, parent):
        super(ExpandBtnLabel, self).__init__(parent)
        self._source_collapsed_pix = QtGui.QPixmap(
            get_style_image_path("branch_closed")
        )
        self._source_expanded_pix = QtGui.QPixmap(
            get_style_image_path("branch_open")
        )

        self._current_image = self._source_collapsed_pix
        self._collapsed = True

    def set_collapsed(self, collapsed):
        if self._collapsed == collapsed:
            return
        self._collapsed = collapsed
        if collapsed:
            self._current_image = self._source_collapsed_pix
        else:
            self._current_image = self._source_expanded_pix
        self._set_resized_pix()

    def resizeEvent(self, event):
        self._set_resized_pix()
        super(ExpandBtnLabel, self).resizeEvent(event)

    def _set_resized_pix(self):
        size = int(self.fontMetrics().height() / 2)
        if size < 1:
            size = 1
        size += size % 2
        self.setPixmap(
            self._current_image.scaled(
                size,
                size,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
        )


class ExpandBtn(ClickableFrame):
    def __init__(self, parent=None):
        super(ExpandBtn, self).__init__(parent)

        pixmap_label = ExpandBtnLabel(self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(pixmap_label)

        self._pixmap_label = pixmap_label

    def set_collapsed(self, collapsed):
        self._pixmap_label.set_collapsed(collapsed)


class ImageButton(QtWidgets.QPushButton):
    """PushButton with icon and size of font.

    Using font metrics height as icon size reference.

    TODO:
    - handle changes of screen (different resolution)
    """

    def __init__(self, *args, **kwargs):
        super(ImageButton, self).__init__(*args, **kwargs)
        self.setObjectName("ImageButton")

    def _change_size(self):
        font_height = self.fontMetrics().height()
        self.setIconSize(QtCore.QSize(font_height, font_height))

    def showEvent(self, event):
        super(ImageButton, self).showEvent(event)

        self._change_size()

    def sizeHint(self):
        return self.iconSize()


class IconButton(QtWidgets.QPushButton):
    """PushButton with icon and size of font.

    Using font metrics height as icon size reference.
    """

    def __init__(self, *args, **kwargs):
        super(IconButton, self).__init__(*args, **kwargs)
        self.setObjectName("IconButton")

    def sizeHint(self):
        result = super(IconButton, self).sizeHint()
        icon_h = self.iconSize().height()
        font_height = self.fontMetrics().height()
        text_set = bool(self.text())
        if not text_set and icon_h < font_height:
            new_size = result.height() - icon_h + font_height
            result.setHeight(new_size)
            result.setWidth(new_size)

        return result


class PixmapLabel(QtWidgets.QLabel):
    """Label resizing image to height of font."""
    def __init__(self, pixmap, parent):
        super(PixmapLabel, self).__init__(parent)
        self._empty_pixmap = QtGui.QPixmap(0, 0)
        self._source_pixmap = pixmap

    def set_source_pixmap(self, pixmap):
        """Change source image."""
        self._source_pixmap = pixmap
        self._set_resized_pix()

    def _get_pix_size(self):
        size = self.fontMetrics().height()
        size += size % 2
        return size, size

    def _set_resized_pix(self):
        if self._source_pixmap is None:
            self.setPixmap(self._empty_pixmap)
            return
        width, height = self._get_pix_size()
        self.setPixmap(
            self._source_pixmap.scaled(
                width,
                height,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
        )

    def resizeEvent(self, event):
        self._set_resized_pix()
        super(PixmapLabel, self).resizeEvent(event)


class OptionalMenu(QtWidgets.QMenu):
    """A subclass of `QtWidgets.QMenu` to work with `OptionalAction`

    This menu has reimplemented `mouseReleaseEvent`, `mouseMoveEvent` and
    `leaveEvent` to provide better action highlighting and triggering for
    actions that were instances of `QtWidgets.QWidgetAction`.

    """
    def mouseReleaseEvent(self, event):
        """Emit option clicked signal if mouse released on it"""
        active = self.actionAt(event.pos())
        if active and active.use_option:
            option = active.widget.option
            if option.is_hovered(event.globalPos()):
                option.clicked.emit()
        super(OptionalMenu, self).mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        """Add highlight to active action"""
        active = self.actionAt(event.pos())
        for action in self.actions():
            action.set_highlight(action is active, event.globalPos())
        super(OptionalMenu, self).mouseMoveEvent(event)

    def leaveEvent(self, event):
        """Remove highlight from all actions"""
        for action in self.actions():
            action.set_highlight(False)
        super(OptionalMenu, self).leaveEvent(event)


class OptionalAction(QtWidgets.QWidgetAction):
    """Menu action with option box

    A menu action like Maya's menu item with option box, implemented by
    subclassing `QtWidgets.QWidgetAction`.

    """

    def __init__(self, label, icon, use_option, parent):
        super(OptionalAction, self).__init__(parent)
        self.label = label
        self.icon = icon
        self.use_option = use_option
        self.option_tip = ""
        self.optioned = False
        self.widget = None

    def createWidget(self, parent):
        widget = OptionalActionWidget(self.label, parent)
        self.widget = widget

        if self.icon:
            widget.setIcon(self.icon)

        if self.use_option:
            widget.option.clicked.connect(self.on_option)
            widget.option.setToolTip(self.option_tip)
        else:
            widget.option.setVisible(False)

        return widget

    def set_option_tip(self, options):
        sep = "\n\n"
        mak = (lambda opt: opt["name"] + " :\n    " + opt["help"])
        self.option_tip = sep.join(mak(opt) for opt in options)

    def on_option(self):
        self.optioned = True

    def set_highlight(self, state, global_pos=None):
        option_state = False
        if self.use_option:
            option_state = self.widget.option.is_hovered(global_pos)
        self.widget.set_hover_properties(state, option_state)


class OptionalActionWidget(QtWidgets.QWidget):
    """Main widget class for `OptionalAction`"""

    def __init__(self, label, parent=None):
        super(OptionalActionWidget, self).__init__(parent)

        body_widget = QtWidgets.QWidget(self)
        body_widget.setObjectName("OptionalActionBody")

        icon = QtWidgets.QLabel(body_widget)
        label = QtWidgets.QLabel(label, body_widget)
        # (NOTE) For removing ugly QLable shadow FX when highlighted in Nuke.
        #   See https://stackoverflow.com/q/52838690/4145300
        label.setStyle(QtWidgets.QStyleFactory.create("Plastique"))
        option = OptionBox(body_widget)
        option.setObjectName("OptionalActionOption")

        icon.setFixedSize(24, 16)
        option.setFixedSize(30, 30)

        body_layout = QtWidgets.QHBoxLayout(body_widget)
        body_layout.setContentsMargins(4, 0, 4, 0)
        body_layout.setSpacing(2)
        body_layout.addWidget(icon)
        body_layout.addWidget(label)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(2, 1, 2, 1)
        layout.setSpacing(0)
        layout.addWidget(body_widget)
        layout.addWidget(option)

        body_widget.setMouseTracking(True)
        label.setMouseTracking(True)
        option.setMouseTracking(True)
        self.setMouseTracking(True)
        self.setFixedHeight(32)

        self.icon = icon
        self.label = label
        self.option = option
        self.body = body_widget

    def set_hover_properties(self, hovered, option_hovered):
        body_state = ""
        option_state = ""
        if hovered:
            body_state = "hover"

        if option_hovered:
            option_state = "hover"

        if self.body.property("state") != body_state:
            self.body.setProperty("state", body_state)
            self.body.style().polish(self.body)

        if self.option.property("state") != option_state:
            self.option.setProperty("state", option_state)
            self.option.style().polish(self.option)

    def setIcon(self, icon):
        pixmap = icon.pixmap(16, 16)
        self.icon.setPixmap(pixmap)


class OptionBox(QtWidgets.QLabel):
    """Option box widget class for `OptionalActionWidget`"""

    clicked = QtCore.Signal()

    def __init__(self, parent):
        super(OptionBox, self).__init__(parent)

        self.setAlignment(QtCore.Qt.AlignCenter)

        icon = qtawesome.icon("fa.sticky-note-o", color="#c6c6c6")
        pixmap = icon.pixmap(18, 18)
        self.setPixmap(pixmap)

    def is_hovered(self, global_pos):
        if global_pos is None:
            return False
        pos = self.mapFromGlobal(global_pos)
        return self.rect().contains(pos)


class OptionDialog(QtWidgets.QDialog):
    """Option dialog shown by option box"""

    def __init__(self, parent=None):
        super(OptionDialog, self).__init__(parent)
        self.setModal(True)
        self._options = dict()

    def create(self, options):
        parser = qargparse.QArgumentParser(arguments=options)

        decision_widget = QtWidgets.QWidget(self)
        accept_btn = QtWidgets.QPushButton("Accept", decision_widget)
        cancel_btn = QtWidgets.QPushButton("Cancel", decision_widget)

        decision_layout = QtWidgets.QHBoxLayout(decision_widget)
        decision_layout.addWidget(accept_btn)
        decision_layout.addWidget(cancel_btn)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(parser)
        layout.addWidget(decision_widget)

        accept_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        parser.changed.connect(self.on_changed)

    def on_changed(self, argument):
        self._options[argument["name"]] = argument.read()

    def parse(self):
        return self._options.copy()
