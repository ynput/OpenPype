"""Puts the selection project into "hiero.selection"""

import hiero


def selectionChanged(event):
    hiero.selection = event.sender.selection()

hiero.core.events.registerInterest("kSelectionChanged", selectionChanged)
