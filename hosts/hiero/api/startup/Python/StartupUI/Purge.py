# Purge Unused Clips - Removes any unused Clips from a Project
# Usage: Copy to ~/.hiero/Python/StartupUI
# Demonstrates the use of hiero.core.find_items module.
# Usage: Right-click on an item in the Bin View > "Purge Unused Clips"
# Result: Any Clips not used in a Sequence in the active project will be removed
# Requires Hiero 1.5v1 or later.
# Version 1.1

import hiero
import hiero.core.find_items
try:
    from PySide.QtGui import *
    from PySide.QtCore import *
except:
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
    from PySide2.QtCore import *


class PurgeUnusedAction(QAction):
    def __init__(self):
        QAction.__init__(self, "Purge Unused Clips", None)
        self.triggered.connect(self.PurgeUnused)
        hiero.core.events.registerInterest("kShowContextMenu/kBin",
                                           self.eventHandler)
        self.setIcon(QIcon("icons:TagDelete.png"))

    # Method to return whether a Bin is empty...
    def binIsEmpty(self, b):
        numBinItems = 0
        bItems = b.items()
        empty = False

        if len(bItems) == 0:
            empty = True
            return empty
        else:
            for b in bItems:
                if isinstance(b, hiero.core.BinItem) or isinstance(
                        b, hiero.core.Bin):
                    numBinItems += 1
            if numBinItems == 0:
                empty = True

        return empty

    def PurgeUnused(self):

        #Get selected items
        item = self.selectedItem
        proj = item.project()

        # Build a list of Projects
        SEQS = hiero.core.findItems(proj, "Sequences")

        # Build a list of Clips
        CLIPSTOREMOVE = hiero.core.findItems(proj, "Clips")

        if len(SEQS) == 0:
            # Present Dialog Asking if User wants to remove Clips
            msgBox = QMessageBox()
            msgBox.setText("Purge Unused Clips")
            msgBox.setInformativeText(
                "You have no Sequences in this Project. Do you want to remove all Clips (%i) from Project: %s?"
                % (len(CLIPSTOREMOVE), proj.name()))
            msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            msgBox.setDefaultButton(QMessageBox.Ok)
            ret = msgBox.exec_()
            if ret == QMessageBox.Cancel:
                print("Not purging anything.")
            elif ret == QMessageBox.Ok:
                with proj.beginUndo("Purge Unused Clips"):
                    BINS = []
                    for clip in CLIPSTOREMOVE:
                        BI = clip.binItem()
                        B = BI.parentBin()
                        BINS += [B]
                        print("Removing: {}".format(BI))
                        try:
                            B.removeItem(BI)
                        except:
                            print("Unable to remove: {}".format(BI))
            return

        # For each sequence, iterate through each track Item, see if the Clip is in the CLIPS list.
        # Remaining items in CLIPS will be removed

        for seq in SEQS:

            #Loop through selected and make folders
            for track in seq:
                for trackitem in track:

                    if trackitem.source() in CLIPSTOREMOVE:
                        CLIPSTOREMOVE.remove(trackitem.source())

        # Present Dialog Asking if User wants to remove Clips
        msgBox = QMessageBox()
        msgBox.setText("Purge Unused Clips")
        msgBox.setInformativeText("Remove %i unused Clips from Project %s?" %
                                  (len(CLIPSTOREMOVE), proj.name()))
        msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msgBox.setDefaultButton(QMessageBox.Ok)
        ret = msgBox.exec_()

        if ret == QMessageBox.Cancel:
            print("Cancel")
            return
        elif ret == QMessageBox.Ok:
            BINS = []
            with proj.beginUndo("Purge Unused Clips"):
                # Delete the rest of the Clips
                for clip in CLIPSTOREMOVE:
                    BI = clip.binItem()
                    B = BI.parentBin()
                    BINS += [B]
                    print("Removing: {}".format(BI))
                    try:
                        B.removeItem(BI)
                    except:
                        print("Unable to remove: {}".format(BI))

    def eventHandler(self, event):
        if not hasattr(event.sender, "selection"):
            # Something has gone wrong, we shouldn't only be here if raised
            # by the Bin view which will give a selection.
            return

        self.selectedItem = None
        s = event.sender.selection()

        if len(s) >= 1:
            self.selectedItem = s[0]
            title = "Purge Unused Clips"
            self.setText(title)
            event.menu.addAction(self)

        return


# Instantiate the action to get it to register itself.
PurgeUnusedAction = PurgeUnusedAction()
