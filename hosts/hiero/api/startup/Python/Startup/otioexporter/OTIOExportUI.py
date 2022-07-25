# -*- coding: utf-8 -*-

__author__ = "Daniel Flehner Heen"
__credits__ = ["Jakub Jezek", "Daniel Flehner Heen"]

import hiero.ui
from .OTIOExportTask import (
    OTIOExportTask,
    OTIOExportPreset
)

try:
    # Hiero >= 11.x
    from PySide2 import QtCore
    from PySide2.QtWidgets import QCheckBox
    from hiero.ui.FnTaskUIFormLayout import TaskUIFormLayout as FormLayout

except ImportError:
    # Hiero <= 10.x
    from PySide import QtCore  # lint:ok
    from PySide.QtGui import QCheckBox, QFormLayout  # lint:ok

    FormLayout = QFormLayout  # lint:ok

from openpype.hosts.hiero.api.otio import hiero_export

class OTIOExportUI(hiero.ui.TaskUIBase):
    def __init__(self, preset):
        """Initialize"""
        hiero.ui.TaskUIBase.__init__(
            self,
            OTIOExportTask,
            preset,
            "OTIO Exporter"
        )

    def includeMarkersCheckboxChanged(self, state):
        # Slot to handle change of checkbox state
        hiero_export.include_tags = state == QtCore.Qt.Checked

    def populateUI(self, widget, exportTemplate):
        layout = widget.layout()
        formLayout = FormLayout()

        # Hiero ~= 10.0v4
        if layout is None:
            layout = formLayout
            widget.setLayout(layout)

        else:
            layout.addLayout(formLayout)

        # Checkboxes for whether the OTIO should contain markers or not
        self.includeMarkersCheckbox = QCheckBox()
        self.includeMarkersCheckbox.setToolTip(
            "Enable to include Tags as markers in the exported OTIO file."
        )
        self.includeMarkersCheckbox.setCheckState(QtCore.Qt.Unchecked)

        if self._preset.properties()["includeTags"]:
            self.includeMarkersCheckbox.setCheckState(QtCore.Qt.Checked)

        self.includeMarkersCheckbox.stateChanged.connect(
            self.includeMarkersCheckboxChanged
        )

        # Add Checkbox to layout
        formLayout.addRow("Include Tags:", self.includeMarkersCheckbox)


hiero.ui.taskUIRegistry.registerTaskUI(
    OTIOExportPreset,
    OTIOExportUI
)
