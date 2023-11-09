""" OpenPype custom script for resetting read nodes start frame values """

# import nuke
# import nukescripts
import importlib

from qtpy import QtWidgets
from qtpy.QtWidgets import QInputDialog, QLineEdit

# class NewQCProjectFromKitsu(nukescripts.PythonPanel):
#     """ Frame Settings Panel """
#     def __init__(self):
#         nukescripts.PythonPanel.__init__(self, "Set Frame Start (Read Node)")

#         # create knobs
#         self.frame = nuke.Int_Knob(
#             'frame', 'Frame Number')
#         self.selected = nuke.Boolean_Knob("selection")
#         # add knobs to panel
#         self.addKnob(self.selected)
#         self.addKnob(self.frame)

#         # set values
#         self.selected.setValue(False)
#         self.frame.setValue(nuke.root().firstFrame())

#     def process(self):
#         """ Process the panel values. """
#         # get values
#         frame = self.frame.value()
#         if self.selected.value():
#             # selected nodes processing
#             if not nuke.selectedNodes():
#                 return
#             for rn_ in nuke.selectedNodes():
#                 if rn_.Class() != "Read":
#                     continue
#                 rn_["frame_mode"].setValue("start_at")
#                 rn_["frame"].setValue(str(frame))
#         else:
#             # all nodes processing
#             for rn_ in nuke.allNodes(filter="Read"):
#                 rn_["frame_mode"].setValue("start_at")
#                 rn_["frame"].setValue(str(frame))


def main():
    print("Hi!")


    url, ok = QInputDialog().getText(None, "New QC Project Playlist",
                                        "Playlist URL:", QLineEdit.Normal)
    # p_ = NewQCProjectFromKitsu()
    # if p_.showModalDialog():
    #     print(p_.process())
