#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "Daniel Flehner Heen"
__credits__ = ["Jakub Jezek", "Daniel Flehner Heen"]

import hiero.ui
import hiero.core

import PySide2.QtWidgets as qw

from openpype.hosts.hiero.api.otio.hiero_import import load_otio


class OTIOProjectSelect(qw.QDialog):

    def __init__(self, projects, *args, **kwargs):
        super(OTIOProjectSelect, self).__init__(*args, **kwargs)
        self.setWindowTitle("Please select active project")
        self.layout = qw.QVBoxLayout()

        self.label = qw.QLabel(
            "Unable to determine which project to import sequence to.\n"
            "Please select one."
        )
        self.layout.addWidget(self.label)

        self.projects = qw.QComboBox()
        self.projects.addItems(map(lambda p: p.name(), projects))
        self.layout.addWidget(self.projects)

        QBtn = qw.QDialogButtonBox.Ok | qw.QDialogButtonBox.Cancel
        self.buttonBox = qw.QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


def get_sequence(view):
    sequence = None
    if isinstance(view, hiero.ui.TimelineEditor):
        sequence = view.sequence()

    elif isinstance(view, hiero.ui.BinView):
        for item in view.selection():
            if not hasattr(item, "acitveItem"):
                continue

            if isinstance(item.activeItem(), hiero.core.Sequence):
                sequence = item.activeItem()

    return sequence


def OTIO_menu_action(event):
    # Menu actions
    otio_import_action = hiero.ui.createMenuAction(
        "Import OTIO...",
        open_otio_file,
        icon=None
    )

    otio_add_track_action = hiero.ui.createMenuAction(
        "New Track(s) from OTIO...",
        open_otio_file,
        icon=None
    )
    otio_add_track_action.setEnabled(False)

    hiero.ui.registerAction(otio_import_action)
    hiero.ui.registerAction(otio_add_track_action)

    view = hiero.ui.currentContextMenuView()

    if view:
        sequence = get_sequence(view)
        if sequence:
            otio_add_track_action.setEnabled(True)

    for action in event.menu.actions():
        if action.text() == "Import":
            action.menu().addAction(otio_import_action)
            action.menu().addAction(otio_add_track_action)

        elif action.text() == "New Track":
            action.menu().addAction(otio_add_track_action)


def open_otio_file():
    files = hiero.ui.openFileBrowser(
        caption="Please select an OTIO file of choice",
        pattern="*.otio",
        requiredExtension=".otio"
    )

    selection = None
    sequence = None

    view = hiero.ui.currentContextMenuView()
    if view:
        sequence = get_sequence(view)
        selection = view.selection()

    if sequence:
        project = sequence.project()

    elif selection:
        project = selection[0].project()

    elif len(hiero.core.projects()) > 1:
        dialog = OTIOProjectSelect(hiero.core.projects())
        if dialog.exec_():
            project = hiero.core.projects()[dialog.projects.currentIndex()]

        else:
            bar = hiero.ui.mainWindow().statusBar()
            bar.showMessage(
                "OTIO Import aborted by user",
                timeout=3000
            )
            return

    else:
        project = hiero.core.projects()[-1]

    for otio_file in files:
        load_otio(otio_file, project, sequence)


# HieroPlayer is quite limited and can't create transitions etc.
if not hiero.core.isHieroPlayer():
    hiero.core.events.registerInterest(
        "kShowContextMenu/kBin",
        OTIO_menu_action
    )
    hiero.core.events.registerInterest(
        "kShowContextMenu/kTimeline",
        OTIO_menu_action
    )
