import os
from . import QtCore, QtGui, QtWidgets
from . import SvgButton
from . import get_resource
from avalon import style


class ComponentItem(QtWidgets.QFrame):
    C_NORMAL = '#777777'
    C_HOVER = '#ffffff'
    C_ACTIVE = '#4BB543'
    C_ACTIVE_HOVER = '#4BF543'

    signal_remove = QtCore.Signal(object)
    signal_thumbnail = QtCore.Signal(object)
    signal_preview = QtCore.Signal(object)
    signal_repre_change = QtCore.Signal(object, object)

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

        self.btn_action_menu = SvgButton(
            get_resource('menu.svg'), 22, 22,
            [self.C_NORMAL, self.C_HOVER],
            frame_image_info, False
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

        expanding_sizePolicy.setHeightForWidth(self.name.sizePolicy().hasHeightForWidth())

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
            QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding
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

        self.preview = SvgButton(
            get_resource('preview.svg'), 64, 18,
            [self.C_NORMAL, self.C_HOVER, self.C_ACTIVE, self.C_ACTIVE_HOVER],
            frame_icons
        )

        self.thumbnail = SvgButton(
            get_resource('thumbnail.svg'), 84, 18,
            [self.C_NORMAL, self.C_HOVER, self.C_ACTIVE, self.C_ACTIVE_HOVER],
            frame_icons
        )

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

        self.remove = SvgButton(
            get_resource('trash.svg'), 22, 22,
            [self.C_NORMAL, self.C_HOVER],
            frame, False
        )

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
        return self.thumbnail.checked

    def change_thumbnail(self, hover=True):
        self.thumbnail.change_checked(hover)

    def is_preview(self):
        return self.preview.checked

    def change_preview(self, hover=True):
        self.preview.change_checked(hover)

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
