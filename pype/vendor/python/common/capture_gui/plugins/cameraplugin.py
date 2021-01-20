import maya.cmds as cmds
from capture_gui.vendor.Qt import QtCore, QtWidgets

import capture_gui.lib as lib
import capture_gui.plugin


class CameraPlugin(capture_gui.plugin.Plugin):
    """Camera widget.

    Allows to select a camera.

    """
    id = "Camera"
    section = "app"
    order = 10

    def __init__(self, parent=None):
        super(CameraPlugin, self).__init__(parent=parent)

        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setContentsMargins(5, 0, 5, 0)
        self.setLayout(self._layout)

        self.cameras = QtWidgets.QComboBox()
        self.cameras.setMinimumWidth(200)

        self.get_active = QtWidgets.QPushButton("Get active")
        self.get_active.setToolTip("Set camera from currently active view")
        self.refresh = QtWidgets.QPushButton("Refresh")
        self.refresh.setToolTip("Refresh the list of cameras")

        self._layout.addWidget(self.cameras)
        self._layout.addWidget(self.get_active)
        self._layout.addWidget(self.refresh)

        # Signals
        self.connections()

        # Force update of the label
        self.set_active_cam()
        self.on_update_label()

    def connections(self):
        self.get_active.clicked.connect(self.set_active_cam)
        self.refresh.clicked.connect(self.on_refresh)

        self.cameras.currentIndexChanged.connect(self.on_update_label)
        self.cameras.currentIndexChanged.connect(self.validate)

    def set_active_cam(self):
        cam = lib.get_current_camera()
        self.on_refresh(camera=cam)

    def select_camera(self, cam):
        if cam:
            # Ensure long name
            cameras = cmds.ls(cam, long=True)
            if not cameras:
                return
            cam = cameras[0]

            # Find the index in the list
            for i in range(self.cameras.count()):
                value = str(self.cameras.itemText(i))
                if value == cam:
                    self.cameras.setCurrentIndex(i)
                    return

    def validate(self):

        errors = []
        camera = self.cameras.currentText()
        if not cmds.objExists(camera):
            errors.append("{} : Selected camera '{}' "
                          "does not exist!".format(self.id, camera))
            self.cameras.setStyleSheet(self.highlight)
        else:
            self.cameras.setStyleSheet("")

        return errors

    def get_outputs(self):
        """Return currently selected camera from combobox."""

        idx = self.cameras.currentIndex()
        camera = str(self.cameras.itemText(idx)) if idx != -1 else None

        return {"camera": camera}

    def on_refresh(self, camera=None):
        """Refresh the camera list with all current cameras in scene.

        A currentIndexChanged signal is only emitted for the cameras combobox
        when the camera is different at the end of the refresh.

        Args:
            camera (str): When name of camera is passed it will try to select
                the camera with this name after the refresh.

        Returns:
            None

        """

        cam = self.get_outputs()['camera']

        # Get original selection
        if camera is None:
            index = self.cameras.currentIndex()
            if index != -1:
                camera = self.cameras.currentText()

        self.cameras.blockSignals(True)

        # Update the list with available cameras
        self.cameras.clear()

        cam_shapes = cmds.ls(type="camera")
        cam_transforms = cmds.listRelatives(cam_shapes,
                                            parent=True,
                                            fullPath=True)
        self.cameras.addItems(cam_transforms)

        # If original selection, try to reselect
        self.select_camera(camera)

        self.cameras.blockSignals(False)

        # If camera changed emit signal
        if cam != self.get_outputs()['camera']:
            idx = self.cameras.currentIndex()
            self.cameras.currentIndexChanged.emit(idx)

    def on_update_label(self):

        cam = self.cameras.currentText()
        cam = cam.rsplit("|", 1)[-1]  # ensure short name
        self.label = "Camera ({0})".format(cam)

        self.label_changed.emit(self.label)
