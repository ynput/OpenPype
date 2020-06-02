import os
from . import QtCore, QtGui, QtWidgets
from . import get_resource
from avalon import style


class ComponentItem(QtWidgets.QFrame):

    signal_remove = QtCore.Signal(object)
    signal_thumbnail = QtCore.Signal(object)
    signal_preview = QtCore.Signal(object)
    signal_repre_change = QtCore.Signal(object, object)

    preview_text = "PREVIEW"
    thumbnail_text = "THUMBNAIL"

    def __init__(self, parent, main_parent):
        super().__init__()
        self.has_valid_repre = True
        self.actions = []
        self.resize(290, 70)
        self.setMinimumSize(QtCore.QSize(0, 70))
        self.parent_list = parent
        self.parent_widget = main_parent
        # Font
        font = QtGui.QFont()
        font.setFamily("DejaVu Sans Condensed")
        font.setPointSize(9)
        font.setBold(True)
        font.setWeight(50)
        font.setKerning(True)

        # Main widgets
        frame = QtWidgets.QFrame(self)
        frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        frame.setFrameShadow(QtWidgets.QFrame.Raised)

        layout_main = QtWidgets.QHBoxLayout(frame)
        layout_main.setSpacing(2)
        layout_main.setContentsMargins(2, 2, 2, 2)

        # Image + Info
        frame_image_info = QtWidgets.QFrame(frame)

        # Layout image info
        layout = QtWidgets.QVBoxLayout(frame_image_info)
        layout.setSpacing(2)
        layout.setContentsMargins(2, 2, 2, 2)

        self.icon = QtWidgets.QLabel(frame)
        self.icon.setMinimumSize(QtCore.QSize(22, 22))
        self.icon.setMaximumSize(QtCore.QSize(22, 22))
        self.icon.setText("")
        self.icon.setScaledContents(True)

        self.btn_action_menu = PngButton(
            name="menu", size=QtCore.QSize(22, 22)
        )

        self.action_menu = QtWidgets.QMenu()

        expanding_sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        expanding_sizePolicy.setHorizontalStretch(0)
        expanding_sizePolicy.setVerticalStretch(0)

        layout.addWidget(self.icon, alignment=QtCore.Qt.AlignCenter)
        layout.addWidget(self.btn_action_menu, alignment=QtCore.Qt.AlignCenter)

        layout_main.addWidget(frame_image_info)

        # Name + representation
        self.name = QtWidgets.QLabel(frame)
        self.file_info = QtWidgets.QLabel(frame)
        self.ext = QtWidgets.QLabel(frame)

        self.name.setFont(font)
        self.file_info.setFont(font)
        self.ext.setFont(font)

        self.file_info.setStyleSheet('padding-left:3px;')

        expanding_sizePolicy.setHeightForWidth(
            self.name.sizePolicy().hasHeightForWidth()
        )

        frame_name_repre = QtWidgets.QFrame(frame)

        self.file_info.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self.ext.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self.name.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)

        layout = QtWidgets.QHBoxLayout(frame_name_repre)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.name, alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(self.file_info, alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(self.ext, alignment=QtCore.Qt.AlignRight)

        frame_name_repre.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        # Repre + icons
        frame_repre_icons = QtWidgets.QFrame(frame)

        frame_repre = QtWidgets.QFrame(frame_repre_icons)

        label_repre = QtWidgets.QLabel()
        label_repre.setText('Representation:')

        self.input_repre = QtWidgets.QLineEdit()
        self.input_repre.setMaximumWidth(50)

        layout = QtWidgets.QHBoxLayout(frame_repre)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(label_repre, alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(self.input_repre, alignment=QtCore.Qt.AlignLeft)

        frame_icons = QtWidgets.QFrame(frame_repre_icons)

        self.preview = LightingButton(self.preview_text)
        self.thumbnail = LightingButton(self.thumbnail_text)

        layout = QtWidgets.QHBoxLayout(frame_icons)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.thumbnail)
        layout.addWidget(self.preview)

        layout = QtWidgets.QHBoxLayout(frame_repre_icons)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(frame_repre, alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(frame_icons, alignment=QtCore.Qt.AlignRight)

        frame_middle = QtWidgets.QFrame(frame)

        layout = QtWidgets.QVBoxLayout(frame_middle)
        layout.setSpacing(0)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.addWidget(frame_name_repre)
        layout.addWidget(frame_repre_icons)

        layout.setStretchFactor(frame_name_repre, 1)
        layout.setStretchFactor(frame_repre_icons, 1)

        layout_main.addWidget(frame_middle)

        self.remove = PngButton(name="trash", size=QtCore.QSize(22, 22))
        layout_main.addWidget(self.remove)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(frame)

        self.preview.setToolTip('Mark component as Preview')
        self.thumbnail.setToolTip('Component will be selected as thumbnail')

        # self.frame.setStyleSheet("border: 1px solid black;")

    def set_context(self, data):
        self.btn_action_menu.setVisible(False)
        self.in_data = data
        self.remove.clicked.connect(self._remove)
        self.thumbnail.clicked.connect(self._thumbnail_clicked)
        self.preview.clicked.connect(self._preview_clicked)
        self.input_repre.textChanged.connect(self._handle_duplicate_repre)
        name = data['name']
        representation = data['representation']
        ext = data['ext']
        file_info = data['file_info']
        thumb = data['thumb']
        prev = data['prev']
        icon = data['icon']

        resource = None
        if icon is not None:
            resource = get_resource('{}.png'.format(icon))

        if resource is None or not os.path.isfile(resource):
            if data['is_sequence']:
                resource = get_resource('files.png')
            else:
                resource = get_resource('file.png')

        pixmap = QtGui.QPixmap(resource)
        self.icon.setPixmap(pixmap)

        self.name.setText(name)
        self.input_repre.setText(representation)
        self.ext.setText('( {} )'.format(ext))
        if file_info is None:
            self.file_info.setVisible(False)
        else:
            self.file_info.setText('[{}]'.format(file_info))

        self.thumbnail.setVisible(thumb)
        self.preview.setVisible(prev)

    def add_action(self, action_name):
        if action_name.lower() == 'split':
            for action in self.actions:
                if action.text() == 'Split to frames':
                    return
            new_action = QtWidgets.QAction('Split to frames', self)
            new_action.triggered.connect(self.split_sequence)
        elif action_name.lower() == 'merge':
            for action in self.actions:
                if action.text() == 'Merge components':
                    return
            new_action = QtWidgets.QAction('Merge components', self)
            new_action.triggered.connect(self.merge_sequence)
        else:
            print('unknown action')
            return
        self.action_menu.addAction(new_action)
        self.actions.append(new_action)
        if not self.btn_action_menu.isVisible():
            self.btn_action_menu.setVisible(True)
            self.btn_action_menu.clicked.connect(self.show_actions)
            self.action_menu.setStyleSheet(style.load_stylesheet())

    def set_repre_name_valid(self, valid):
        self.has_valid_repre = valid
        if valid:
            self.input_repre.setStyleSheet("")
        else:
            self.input_repre.setStyleSheet("border: 1px solid red;")

    def split_sequence(self):
        self.parent_widget.split_items(self)

    def merge_sequence(self):
        self.parent_widget.merge_items(self)

    def show_actions(self):
        position = QtGui.QCursor().pos()
        self.action_menu.popup(position)

    def _remove(self):
        self.signal_remove.emit(self)

    def _thumbnail_clicked(self):
        self.signal_thumbnail.emit(self)

    def _preview_clicked(self):
        self.signal_preview.emit(self)

    def _handle_duplicate_repre(self, repre_name):
        self.signal_repre_change.emit(self, repre_name)

    def is_thumbnail(self):
        return self.thumbnail.isChecked()

    def change_thumbnail(self, hover=True):
        self.thumbnail.setChecked(hover)

    def is_preview(self):
        return self.preview.isChecked()

    def change_preview(self, hover=True):
        self.preview.setChecked(hover)

    def collect_data(self):
        in_files = self.in_data['files']
        staging_dir = os.path.dirname(in_files[0])

        files = [os.path.basename(file) for file in in_files]
        if len(files) == 1:
            files = files[0]

        data = {
            'ext': self.in_data['ext'],
            'label': self.name.text(),
            'name': self.input_repre.text(),
            'stagingDir': staging_dir,
            'files': files,
            'thumbnail': self.is_thumbnail(),
            'preview': self.is_preview()
        }

        if ("frameStart" in self.in_data and "frameEnd" in self.in_data):
            data["frameStart"] = self.in_data["frameStart"]
            data["frameEnd"] = self.in_data["frameEnd"]

        if 'fps' in self.in_data:
            data['fps'] = self.in_data['fps']

        return data


class LightingButton(QtWidgets.QPushButton):
    lightingbtnstyle = """
    QPushButton {
        font: %(font_size_pt)spt;
        text-align: center;
        color: #777777;
        background-color: transparent;
        border-width: 1px;
        border-color: #777777;
        border-style: solid;
        padding-top: 0px;
        padding-bottom: 0px;
        padding-left: 3px;
        padding-right: 3px;
        border-radius: 3px;
    }

    QPushButton:hover {
        border-color: #cccccc;
        color: #cccccc;
    }

    QPushButton:pressed {
        border-color: #ffffff;
        color: #ffffff;
    }

    QPushButton:disabled {
        border-color: #3A3939;
        color: #3A3939;
    }

    QPushButton:checked {
        border-color: #4BB543;
        color: #4BB543;
    }

    QPushButton:checked:hover {
        border-color: #4Bd543;
        color: #4Bd543;
    }

    QPushButton:checked:pressed {
        border-color: #4BF543;
        color: #4BF543;
    }
    """

    def __init__(self, text, font_size_pt=8, *args, **kwargs):
        super(LightingButton, self).__init__(text, *args, **kwargs)
        self.setStyleSheet(self.lightingbtnstyle % {
            "font_size_pt": font_size_pt
        })
        self.setCheckable(True)


class PngFactory:
    png_names = {
        "trash": {
            "normal": QtGui.QIcon(get_resource("trash.png")),
            "hover": QtGui.QIcon(get_resource("trash_hover.png")),
            "pressed": QtGui.QIcon(get_resource("trash_pressed.png")),
            "pressed_hover": QtGui.QIcon(
                get_resource("trash_pressed_hover.png")
            ),
            "disabled": QtGui.QIcon(get_resource("trash_disabled.png"))
        },

        "menu": {
            "normal": QtGui.QIcon(get_resource("menu.png")),
            "hover": QtGui.QIcon(get_resource("menu_hover.png")),
            "pressed": QtGui.QIcon(get_resource("menu_pressed.png")),
            "pressed_hover": QtGui.QIcon(
                get_resource("menu_pressed_hover.png")
            ),
            "disabled": QtGui.QIcon(get_resource("menu_disabled.png"))
        }
    }


class PngButton(QtWidgets.QPushButton):
    png_button_style = """
    QPushButton {
        border: none;
        background-color: transparent;
        padding-top: 0px;
        padding-bottom: 0px;
        padding-left: 0px;
        padding-right: 0px;
    }
    QPushButton:hover {}
    QPushButton:pressed {}
    QPushButton:disabled {}
    QPushButton:checked {}
    QPushButton:checked:hover {}
    QPushButton:checked:pressed {}
    """

    def __init__(
        self, name=None, path=None, hover_path=None, pressed_path=None,
        hover_pressed_path=None, disabled_path=None,
        size=None, *args, **kwargs
    ):
        self._hovered = False
        self._pressed = False
        super(PngButton, self).__init__(*args, **kwargs)
        self.setStyleSheet(self.png_button_style)

        png_dict = {}
        if name:
            png_dict = PngFactory.png_names.get(name) or {}
            if not png_dict:
                print((
                    "WARNING: There is not set icon with name \"{}\""
                    "in PngFactory!"
                ).format(name))

        ico_normal = png_dict.get("normal")
        ico_hover = png_dict.get("hover")
        ico_pressed = png_dict.get("pressed")
        ico_hover_pressed = png_dict.get("pressed_hover")
        ico_disabled = png_dict.get("disabled")

        if path:
            ico_normal = QtGui.QIcon(path)
        if hover_path:
            ico_hover = QtGui.QIcon(hover_path)

        if pressed_path:
            ico_pressed = QtGui.QIcon(hover_path)

        if hover_pressed_path:
            ico_hover_pressed = QtGui.QIcon(hover_pressed_path)

        if disabled_path:
            ico_disabled = QtGui.QIcon(disabled_path)

        self.setIcon(ico_normal)
        if size:
            self.setIconSize(size)
            self.setMaximumSize(size)

        self.ico_normal = ico_normal
        self.ico_hover = ico_hover
        self.ico_pressed = ico_pressed
        self.ico_hover_pressed = ico_hover_pressed
        self.ico_disabled = ico_disabled

    def setDisabled(self, in_bool):
        super(PngButton, self).setDisabled(in_bool)
        icon = self.ico_normal
        if in_bool and self.ico_disabled:
            icon = self.ico_disabled
        self.setIcon(icon)

    def enterEvent(self, event):
        self._hovered = True
        if not self.isEnabled():
            return
        icon = self.ico_normal
        if self.ico_hover:
            icon = self.ico_hover

        if self._pressed and self.ico_hover_pressed:
            icon = self.ico_hover_pressed

        if self.icon() != icon:
            self.setIcon(icon)

    def mouseMoveEvent(self, event):
        super(PngButton, self).mouseMoveEvent(event)
        if self._pressed:
            mouse_pos = event.pos()
            hovering = self.rect().contains(mouse_pos)
            if hovering and not self._hovered:
                self.enterEvent(event)
            elif not hovering and self._hovered:
                self.leaveEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        if not self.isEnabled():
            return
        icon = self.ico_normal
        if self._pressed and self.ico_pressed:
            icon = self.ico_pressed

        if self.icon() != icon:
            self.setIcon(icon)

    def mousePressEvent(self, event):
        self._pressed = True
        if not self.isEnabled():
            return
        icon = self.ico_hover
        if self.ico_pressed:
            icon = self.ico_pressed

        if self.ico_hover_pressed:
            mouse_pos = event.pos()
            if self.rect().contains(mouse_pos):
                icon = self.ico_hover_pressed

        if icon is None:
            icon = self.ico_normal

        if self.icon() != icon:
            self.setIcon(icon)

    def mouseReleaseEvent(self, event):
        if not self.isEnabled():
            return
        if self._pressed:
            self._pressed = False
            mouse_pos = event.pos()
            if self.rect().contains(mouse_pos):
                self.clicked.emit()

        icon = self.ico_normal
        if self._hovered and self.ico_hover:
            icon = self.ico_hover

        if self.icon() != icon:
            self.setIcon(icon)
