from . import QtCore, QtGui, QtWidgets
from . import SvgButton
from . import get_resource


class ComponentWidget(QtWidgets.QFrame):
    C_NORMAL = '#777777'
    C_HOVER = '#ffffff'
    C_ACTIVE = '#4BB543'
    C_ACTIVE_HOVER = '#4BF543'
    signal_remove = QtCore.Signal(object)

    def __init__(self, parent):
        super().__init__()
        self.resize(290, 70)
        self.setMinimumSize(QtCore.QSize(0, 70))
        self.parent_item = parent
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

        self.info = SvgButton(
            get_resource('information.svg'), 22, 22,
            [self.C_NORMAL, self.C_HOVER],
            frame_image_info, False
        )

        expanding_sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        expanding_sizePolicy.setHorizontalStretch(0)
        expanding_sizePolicy.setVerticalStretch(0)

        layout.addWidget(self.icon, alignment=QtCore.Qt.AlignCenter)
        layout.addWidget(self.info, alignment=QtCore.Qt.AlignCenter)

        layout_main.addWidget(frame_image_info)

        # Name + representation
        self.name = QtWidgets.QLabel(frame)
        self.frames = QtWidgets.QLabel(frame)
        self.ext = QtWidgets.QLabel(frame)

        self.name.setFont(font)
        self.frames.setFont(font)
        self.ext.setFont(font)

        self.frames.setStyleSheet('padding-left:3px;')

        expanding_sizePolicy.setHeightForWidth(self.name.sizePolicy().hasHeightForWidth())

        frame_name_repre = QtWidgets.QFrame(frame)

        self.frames.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self.ext.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self.name.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)

        layout = QtWidgets.QHBoxLayout(frame_name_repre)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.name, alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(self.frames, alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(self.ext, alignment=QtCore.Qt.AlignRight)

        frame_name_repre.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding
        )

        # Frames + icons
        frame_repre_icons = QtWidgets.QFrame(frame)

        label_repre = QtWidgets.QLabel()
        label_repre.setText('Representation:')

        self.input_repre = QtWidgets.QLineEdit()
        self.input_repre.setMaximumWidth(50)

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

        layout.addWidget(label_repre, alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(self.input_repre, alignment=QtCore.Qt.AlignLeft)
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

        self.remove.clicked.connect(self._remove)
        name = data['name']
        representation = data['representation']
        ext = data['ext']
        file_info = data['file_info']
        thumb = data['thumb']
        prev = data['prev']
        info = data['info']
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

        # self.thumbnail.setVisible(thumb)
        # self.preview.setVisible(prev)

    def _remove(self):
        self.signal_remove.emit(self.parent_item)
