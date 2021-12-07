import hiero.core
import hiero.ui
try:
    from PySide.QtGui import *
    from PySide.QtCore import *
except:
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
    from PySide2.QtCore import *


def setPosterFrame(posterFrame=.5):
    """
    Update the poster frame of the given clipItmes
    posterFrame = .5 uses the centre frame, a value of 0 uses the first frame, a value of 1 uses the last frame
    """
    view = hiero.ui.activeView()

    selectedBinItems = view.selection()
    selectedClipItems = [(item.activeItem()
                          if hasattr(item, "activeItem") else item)
                         for item in selectedBinItems]

    for clip in selectedClipItems:
        centreFrame = int(clip.duration() * posterFrame)
        clip.setPosterFrame(centreFrame)


class SetPosterFrameAction(QAction):
    def __init__(self):
        QAction.__init__(self, "Set Poster Frame (centre)", None)
        self._selection = None

        self.triggered.connect(lambda: setPosterFrame(.5))
        hiero.core.events.registerInterest("kShowContextMenu/kBin",
                                           self.eventHandler)

    def eventHandler(self, event):
        view = event.sender
        # Add the Menu to the right-click menu
        event.menu.addAction(self)


# The act of initialising the action adds it to the right-click menu...
SetPosterFrameAction()
