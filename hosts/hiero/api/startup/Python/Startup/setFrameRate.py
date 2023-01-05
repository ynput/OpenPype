# setFrameRate - adds a Right-click menu to the Project Bin view, allowing multiple BinItems (Clips/Sequences) to have their frame rates set.
# Install in: ~/.hiero/Python/StartupUI
# Requires 1.5v1 or later

import hiero.core
import hiero.ui
try:
  from PySide.QtGui import *
  from PySide.QtCore import *
except:
  from PySide2.QtGui import *
  from PySide2.QtCore import *
  from PySide2.QtWidgets import *

# Dialog for setting a Custom frame rate.
class SetFrameRateDialog(QDialog):

  def __init__(self,itemSelection=None,parent=None):
    super(SetFrameRateDialog, self).__init__(parent)
    self.setWindowTitle("Set Custom Frame Rate")
    self.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Fixed )
    layout = QFormLayout()
    self._itemSelection = itemSelection

    self._frameRateField = QLineEdit()
    self._frameRateField.setToolTip("Enter custom frame rate here.")
    self._frameRateField.setValidator(QDoubleValidator(1, 99, 3, self))
    self._frameRateField.textChanged.connect(self._textChanged)
    layout.addRow("Enter fps: ",self._frameRateField)

    # Standard buttons for Add/Cancel
    self._buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    self._buttonbox.accepted.connect(self.accept)
    self._buttonbox.rejected.connect(self.reject)
    self._buttonbox.button(QDialogButtonBox.Ok).setEnabled(False)
    layout.addRow("",self._buttonbox)
    self.setLayout(layout)

  def _updateOkButtonState(self):
    # Cancel is always an option but only enable Ok if there is some text.
    currentFramerate = float(self.currentFramerateString())
    enableOk = False
    enableOk = ((currentFramerate > 0.0) and (currentFramerate <= 250.0))
    print("enabledOk", enableOk)
    self._buttonbox.button(QDialogButtonBox.Ok).setEnabled(enableOk)

  def _textChanged(self, newText):
    self._updateOkButtonState()

  # Returns the current frame rate as a string
  def currentFramerateString(self):
    return str(self._frameRateField.text())

  # Presents the Dialog and sets the Frame rate from a selection
  def showDialogAndSetFrameRateFromSelection(self):

    if self._itemSelection is not None:
      if self.exec_():
        # For the Undo loop...

        # Construct an TimeBase object for setting the Frame Rate (fps)
        fps = hiero.core.TimeBase().fromString(self.currentFramerateString())


        # Set the frame rate for the selected BinItmes
        for item in self._itemSelection:
          item.setFramerate(fps)
    return

# This is just a convenience method for returning QActions with a title, triggered method and icon.
def makeAction(title, method, icon = None):
  action = QAction(title,None)
  action.setIcon(QIcon(icon))

  # We do this magic, so that the title string from the action is used to set the frame rate!
  def methodWrapper():
    method(title)

  action.triggered.connect( methodWrapper )
  return action

# Menu which adds a Set Frame Rate Menu to Project Bin view
class SetFrameRateMenu:

  def __init__(self):
      self._frameRateMenu = None
      self._frameRatesDialog = None


      # ant: Could use hiero.core.defaultFrameRates() here but messes up with string matching because we seem to mix decimal points
      self.frameRates = ["8","12","12.50","15","23.98","24","25","29.97","30","48","50","59.94","60"]
      hiero.core.events.registerInterest("kShowContextMenu/kBin", self.binViewEventHandler)

      self.menuActions = []

  def createFrameRateMenus(self,selection):
    selectedClipFPS  = [str(bi.activeItem().framerate()) for bi in selection if (isinstance(bi,hiero.core.BinItem) and hasattr(bi,"activeItem"))]
    selectedClipFPS = hiero.core.util.uniquify(selectedClipFPS)
    sameFrameRate = len(selectedClipFPS)==1
    self.menuActions = []
    for fps in self.frameRates:
      if fps in selectedClipFPS:
        if sameFrameRate:
          self.menuActions+=[makeAction(fps,self.setFrameRateFromMenuSelection, icon="icons:Ticked.png")]
        else:
          self.menuActions+=[makeAction(fps,self.setFrameRateFromMenuSelection, icon="icons:remove active.png")]
      else:
        self.menuActions+=[makeAction(fps,self.setFrameRateFromMenuSelection, icon=None)]

    # Now add Custom... menu
    self.menuActions += [makeAction(
      "Custom...", self.setFrameRateFromMenuSelection, icon=None)
      ]

    frameRateMenu = QMenu("Set Frame Rate")
    for a in self.menuActions:
      frameRateMenu.addAction(a)

    return frameRateMenu

  def setFrameRateFromMenuSelection(self, menuSelectionFPS):

    selectedBinItems  = [bi.activeItem() for bi in self._selection if (isinstance(bi,hiero.core.BinItem) and hasattr(bi,"activeItem"))]
    currentProject = selectedBinItems[0].project()

    with currentProject.beginUndo("Set Frame Rate"):
      if menuSelectionFPS == "Custom...":
        self._frameRatesDialog = SetFrameRateDialog(itemSelection = selectedBinItems )
        self._frameRatesDialog.showDialogAndSetFrameRateFromSelection()

      else:
        for b in selectedBinItems:
          b.setFramerate(hiero.core.TimeBase().fromString(menuSelectionFPS))

    return

  # This handles events from the Project Bin View
  def binViewEventHandler(self,event):
    if not hasattr(event.sender, "selection"):
      # Something has gone wrong, we should only be here if raised
      # by the Bin view which gives a selection.
      return

    # Reset the selection to None...
    self._selection = None
    s = event.sender.selection()

    # Return if there's no Selection. We won't add the Menu.
    if s == None:
      return
    # Filter the selection to BinItems
    self._selection = [item for item in s if isinstance(item, hiero.core.BinItem)]
    if len(self._selection)==0:
      return
    # Creating the menu based on items selected, to highlight which frame rates are contained

    self._frameRateMenu = self.createFrameRateMenus(self._selection)

    # Insert the Set Frame Rate Button before the Set Media Colour Transform Action
    for action in event.menu.actions():
      if str(action.text()) == "Set Media Colour Transform":
        event.menu.insertMenu(action, self._frameRateMenu)
        break

# Instantiate the Menu to get it to register itself.
SetFrameRateMenu = SetFrameRateMenu()