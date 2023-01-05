# PimpMySpreadsheet 1.0, Antony Nasce, 23/05/13.
# Adds custom spreadsheet columns and right-click menu for setting the Shot Status, and Artist Shot Assignment.
# gStatusTags is a global dictionary of key(status)-value(icon) pairs, which can be overridden with custom icons if required
# Requires Hiero 1.7v2 or later.
# Install Instructions: Copy to ~/.hiero/Python/StartupUI

import hiero.core
import hiero.ui

try:
    from PySide.QtGui import *
    from PySide.QtCore import *
except:
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
    from PySide2.QtCore import *

# Set to True, if you wat "Set Status" right-click menu, False if not
kAddStatusMenu = True

# Set to True, if you wat "Assign Artist" right-click menu, False if not
kAssignArtistMenu = True

# Global list of Artist Name Dictionaries
# Note: Override this to add different names, icons, department, IDs.
gArtistList = [{
    "artistName": "John Smith",
    "artistIcon": "icons:TagActor.png",
    "artistDepartment": "3D",
    "artistID": 0
}, {
    "artistName": "Savlvador Dali",
    "artistIcon": "icons:TagActor.png",
    "artistDepartment": "Roto",
    "artistID": 1
}, {
    "artistName": "Leonardo Da Vinci",
    "artistIcon": "icons:TagActor.png",
    "artistDepartment": "Paint",
    "artistID": 2
}, {
    "artistName": "Claude Monet",
    "artistIcon": "icons:TagActor.png",
    "artistDepartment": "Comp",
    "artistID": 3
}, {
    "artistName": "Pablo Picasso",
    "artistIcon": "icons:TagActor.png",
    "artistDepartment": "Animation",
    "artistID": 4
}]

# Global Dictionary of Status Tags.
# Note: This can be overwritten if you want to add a new status cellType or custom icon
# Override the gStatusTags dictionary by adding your own "Status":"Icon.png" key-value pairs.
# Add new custom keys like so: gStatusTags["For Client"] = "forClient.png"
gStatusTags = {
    "Approved": "icons:status/TagApproved.png",
    "Unapproved": "icons:status/TagUnapproved.png",
    "Ready To Start": "icons:status/TagReadyToStart.png",
    "Blocked": "icons:status/TagBlocked.png",
    "On Hold": "icons:status/TagOnHold.png",
    "In Progress": "icons:status/TagInProgress.png",
    "Awaiting Approval": "icons:status/TagAwaitingApproval.png",
    "Omitted": "icons:status/TagOmitted.png",
    "Final": "icons:status/TagFinal.png"
}


# The Custom Spreadsheet Columns
class CustomSpreadsheetColumns(QObject):
    """
    A class defining custom columns for Hiero's spreadsheet view. This has a similar, but
    slightly simplified, interface to the QAbstractItemModel and QItemDelegate classes.
  """
    global gStatusTags
    global gArtistList

    # Ideally, we'd set this list on a Per Item basis, but this is expensive for a large mixed selection
    standardColourSpaces = [
        "linear", "sRGB", "rec709", "Cineon", "Gamma1.8", "Gamma2.2",
        "Panalog", "REDLog", "ViperLog"
    ]
    arriColourSpaces = [
        "Video - Rec709", "LogC - Camera Native", "Video - P3", "ACES",
        "LogC - Film", "LogC - Wide Gamut"
    ]
    r3dColourSpaces = [
        "Linear", "Rec709", "REDspace", "REDlog", "PDlog685", "PDlog985",
        "CustomPDlog", "REDgamma", "SRGB", "REDlogFilm", "REDgamma2",
        "REDgamma3"
    ]
    gColourSpaces = standardColourSpaces + arriColourSpaces + r3dColourSpaces

    currentView = hiero.ui.activeView()

    # This is the list of Columns available
    gCustomColumnList = [
        {
            "name": "Tags",
            "cellType": "readonly"
        },
        {
            "name": "Colourspace",
            "cellType": "dropdown"
        },
        {
            "name": "Notes",
            "cellType": "readonly"
        },
        {
            "name": "FileType",
            "cellType": "readonly"
        },
        {
            "name": "Shot Status",
            "cellType": "dropdown"
        },
        {
            "name": "Thumbnail",
            "cellType": "readonly"
        },
        {
            "name": "MediaType",
            "cellType": "readonly"
        },
        {
            "name": "Width",
            "cellType": "readonly"
        },
        {
            "name": "Height",
            "cellType": "readonly"
        },
        {
            "name": "Pixel Aspect",
            "cellType": "readonly"
        },
        {
            "name": "Artist",
            "cellType": "dropdown"
        },
        {
            "name": "Department",
            "cellType": "readonly"
        },
    ]

    def numColumns(self):
        """
      Return the number of custom columns in the spreadsheet view
    """
        return len(self.gCustomColumnList)

    def columnName(self, column):
        """
      Return the name of a custom column
    """
        return self.gCustomColumnList[column]["name"]

    def getTagsString(self, item):
        """
      Convenience method for returning all the Notes in a Tag as a string
    """
        tagNames = []
        tags = item.tags()
        for tag in tags:
            tagNames += [tag.name()]
        tagNameString = ','.join(tagNames)
        return tagNameString

    def getNotes(self, item):
        """
      Convenience method for returning all the Notes in a Tag as a string
    """
        notes = ""
        tags = item.tags()
        for tag in tags:
            note = tag.note()
            if len(note) > 0:
                notes += tag.note() + ', '
        return notes[:-2]

    def getData(self, row, column, item):
        """
      Return the data in a cell
    """
        currentColumn = self.gCustomColumnList[column]
        if currentColumn["name"] == "Tags":
            return self.getTagsString(item)

        if currentColumn["name"] == "Colourspace":
            try:
                colTransform = item.sourceMediaColourTransform()
            except:
                colTransform = "--"
            return colTransform

        if currentColumn["name"] == "Notes":
            try:
                note = self.getNotes(item)
            except:
                note = ""
            return note

        if currentColumn["name"] == "FileType":
            fileType = "--"
            M = item.source().mediaSource().metadata()
            if M.hasKey("foundry.source.type"):
                fileType = M.value("foundry.source.type")
            elif M.hasKey("media.input.filereader"):
                fileType = M.value("media.input.filereader")
            return fileType

        if currentColumn["name"] == "Shot Status":
            status = item.status()
            if not status:
                status = "--"
            return str(status)

        if currentColumn["name"] == "MediaType":
            M = item.mediaType()
            return str(M).split("MediaType")[-1].replace(".k", "")

        if currentColumn["name"] == "Thumbnail":
            return str(item.eventNumber())

        if currentColumn["name"] == "Width":
            return str(item.source().format().width())

        if currentColumn["name"] == "Height":
            return str(item.source().format().height())

        if currentColumn["name"] == "Pixel Aspect":
            return str(item.source().format().pixelAspect())

        if currentColumn["name"] == "Artist":
            if item.artist():
                name = item.artist()["artistName"]
                return name
            else:
                return "--"

        if currentColumn["name"] == "Department":
            if item.artist():
                dep = item.artist()["artistDepartment"]
                return dep
            else:
                return "--"

        return ""

    def setData(self, row, column, item, data):
        """
      Set the data in a cell - unused in this example
    """

        return None

    def getTooltip(self, row, column, item):
        """
      Return the tooltip for a cell
    """
        currentColumn = self.gCustomColumnList[column]
        if currentColumn["name"] == "Tags":
            return str([item.name() for item in item.tags()])

        if currentColumn["name"] == "Notes":
            return str(self.getNotes(item))
        return ""

    def getFont(self, row, column, item):
        """
      Return the tooltip for a cell
    """
        return None

    def getBackground(self, row, column, item):
        """
      Return the background colour for a cell
    """
        if not item.source().mediaSource().isMediaPresent():
            return QColor(80, 20, 20)
        return None

    def getForeground(self, row, column, item):
        """
      Return the text colour for a cell
    """
        #if column == 1:
        #  return QColor(255, 64, 64)
        return None

    def getIcon(self, row, column, item):
        """
      Return the icon for a cell
    """
        currentColumn = self.gCustomColumnList[column]
        if currentColumn["name"] == "Colourspace":
            return QIcon("icons:LUT.png")

        if currentColumn["name"] == "Shot Status":
            status = item.status()
            if status:
                return QIcon(gStatusTags[status])

        if currentColumn["name"] == "MediaType":
            mediaType = item.mediaType()
            if mediaType == hiero.core.TrackItem.kVideo:
                return QIcon("icons:VideoOnly.png")
            elif mediaType == hiero.core.TrackItem.kAudio:
                return QIcon("icons:AudioOnly.png")

        if currentColumn["name"] == "Artist":
            try:
                return QIcon(item.artist()["artistIcon"])
            except:
                return None
        return None

    def getSizeHint(self, row, column, item):
        """
      Return the size hint for a cell
    """
        currentColumnName = self.gCustomColumnList[column]["name"]

        if currentColumnName == "Thumbnail":
            return QSize(90, 50)

        return QSize(50, 50)

    def paintCell(self, row, column, item, painter, option):
        """
      Paint a custom cell. Return True if the cell was painted, or False to continue
      with the default cell painting.
    """
        currentColumn = self.gCustomColumnList[column]
        if currentColumn["name"] == "Tags":
            if option.state & QStyle.State_Selected:
                painter.fillRect(option.rect, option.palette.highlight())
            iconSize = 20
            r = QRect(option.rect.x(),
                      option.rect.y() + (option.rect.height() - iconSize) / 2,
                      iconSize, iconSize)
            tags = item.tags()
            if len(tags) > 0:
                painter.save()
                painter.setClipRect(option.rect)
                for tag in item.tags():
                    M = tag.metadata()
                    if not (M.hasKey("tag.status")
                            or M.hasKey("tag.artistID")):
                        QIcon(tag.icon()).paint(painter, r, Qt.AlignLeft)
                        r.translate(r.width() + 2, 0)
                painter.restore()
                return True

        if currentColumn["name"] == "Thumbnail":
            imageView = None
            pen = QPen()
            r = QRect(option.rect.x() + 2, (option.rect.y() +
                                            (option.rect.height() - 46) / 2),
                      85, 46)
            if not item.source().mediaSource().isMediaPresent():
                imageView = QImage("icons:Offline.png")
                pen.setColor(QColor(Qt.red))

            if item.mediaType() == hiero.core.TrackItem.MediaType.kAudio:
                imageView = QImage("icons:AudioOnly.png")
                #pen.setColor(QColor(Qt.green))
                painter.fillRect(r, QColor(45, 59, 45))

            if option.state & QStyle.State_Selected:
                painter.fillRect(option.rect, option.palette.highlight())

            tags = item.tags()
            painter.save()
            painter.setClipRect(option.rect)

            if not imageView:
                try:
                    imageView = item.thumbnail(item.sourceIn())
                    pen.setColor(QColor(20, 20, 20))
                # If we're here, we probably have a TC error, no thumbnail, so get it from the source Clip...
                except:
                    pen.setColor(QColor(Qt.red))

            if not imageView:
                try:
                    imageView = item.source().thumbnail()
                    pen.setColor(QColor(Qt.yellow))
                except:
                    imageView = QImage("icons:Offline.png")
                    pen.setColor(QColor(Qt.red))

            QIcon(QPixmap.fromImage(imageView)).paint(painter, r,
                                                      Qt.AlignCenter)
            painter.setPen(pen)
            painter.drawRoundedRect(r, 1, 1)
            painter.restore()
            return True

        return False

    def createEditor(self, row, column, item, view):
        """
      Create an editing widget for a custom cell
    """
        self.currentView = view

        currentColumn = self.gCustomColumnList[column]
        if currentColumn["cellType"] == "readonly":
            cle = QLabel()
            cle.setEnabled(False)
            cle.setVisible(False)
            return cle

        if currentColumn["name"] == "Colourspace":
            cb = QComboBox()
            for colourspace in self.gColourSpaces:
                cb.addItem(colourspace)
            cb.currentIndexChanged.connect(self.colourspaceChanged)
            return cb

        if currentColumn["name"] == "Shot Status":
            cb = QComboBox()
            cb.addItem("")
            for key in gStatusTags.keys():
                cb.addItem(QIcon(gStatusTags[key]), key)
            cb.addItem("--")
            cb.currentIndexChanged.connect(self.statusChanged)

            return cb

        if currentColumn["name"] == "Artist":
            cb = QComboBox()
            cb.addItem("")
            for artist in gArtistList:
                cb.addItem(artist["artistName"])
            cb.addItem("--")
            cb.currentIndexChanged.connect(self.artistNameChanged)
            return cb
        return None

    def setModelData(self, row, column, item, editor):
        return False

    def dropMimeData(self, row, column, item, data, items):
        """
      Handle a drag and drop operation - adds a Dragged Tag to the shot
    """
        for thing in items:
            if isinstance(thing, hiero.core.Tag):
                item.addTag(thing)
        return None

    def colourspaceChanged(self, index):
        """
      This method is called when Colourspace widget changes index.
    """
        index = self.sender().currentIndex()
        colourspace = self.gColourSpaces[index]
        selection = self.currentView.selection()
        project = selection[0].project()
        with project.beginUndo("Set Colourspace"):
            items = [
                item for item in selection
                if (item.mediaType() == hiero.core.TrackItem.MediaType.kVideo)
            ]
            for trackItem in items:
                trackItem.setSourceMediaColourTransform(colourspace)

    def statusChanged(self, arg):
        """
      This method is called when Shot Status widget changes index.
    """
        view = hiero.ui.activeView()
        selection = view.selection()
        status = self.sender().currentText()
        project = selection[0].project()
        with project.beginUndo("Set Status"):
            # A string of "--" characters denotes clear the status
            if status != "--":
                for trackItem in selection:
                    trackItem.setStatus(status)
            else:
                for trackItem in selection:
                    tTags = trackItem.tags()
                    for tag in tTags:
                        if tag.metadata().hasKey("tag.status"):
                            trackItem.removeTag(tag)
                            break

    def artistNameChanged(self, arg):
        """
      This method is called when Artist widget changes index.
    """
        view = hiero.ui.activeView()
        selection = view.selection()
        name = self.sender().currentText()
        project = selection[0].project()
        with project.beginUndo("Assign Artist"):
            # A string of "--" denotes clear the assignee...
            if name != "--":
                for trackItem in selection:
                    trackItem.setArtistByName(name)
            else:
                for trackItem in selection:
                    tTags = trackItem.tags()
                    for tag in tTags:
                        if tag.metadata().hasKey("tag.artistID"):
                            trackItem.removeTag(tag)
                            break


def _getArtistFromID(self, artistID):
    """ getArtistFromID -> returns an artist dictionary, by their given ID"""
    global gArtistList
    artist = [
        element for element in gArtistList
        if element["artistID"] == int(artistID)
    ]
    if not artist:
        return None
    return artist[0]


def _getArtistFromName(self, artistName):
    """ getArtistFromID -> returns an artist dictionary, by their given ID """
    global gArtistList
    artist = [
        element for element in gArtistList
        if element["artistName"] == artistName
    ]
    if not artist:
        return None
    return artist[0]


def _artist(self):
    """_artist -> Returns the artist dictionary assigned to this shot"""
    artist = None
    tags = self.tags()
    for tag in tags:
        if tag.metadata().hasKey("tag.artistID"):
            artistID = tag.metadata().value("tag.artistID")
            artist = self.getArtistFromID(artistID)
    return artist


def _updateArtistTag(self, artistDict):
    # A shot will only have one artist assigned. Check if one exists and set accordingly

    artistTag = None
    tags = self.tags()
    for tag in tags:
        if tag.metadata().hasKey("tag.artistID"):
            artistTag = tag
            break

    if not artistTag:
        artistTag = hiero.core.Tag("Artist")
        artistTag.setIcon(artistDict["artistIcon"])
        artistTag.metadata().setValue("tag.artistID",
                                      str(artistDict["artistID"]))
        artistTag.metadata().setValue("tag.artistName",
                                      str(artistDict["artistName"]))
        artistTag.metadata().setValue("tag.artistDepartment",
                                      str(artistDict["artistDepartment"]))
        self.sequence().editFinished()
        self.addTag(artistTag)
        self.sequence().editFinished()
        return

    artistTag.setIcon(artistDict["artistIcon"])
    artistTag.metadata().setValue("tag.artistID", str(artistDict["artistID"]))
    artistTag.metadata().setValue("tag.artistName",
                                  str(artistDict["artistName"]))
    artistTag.metadata().setValue("tag.artistDepartment",
                                  str(artistDict["artistDepartment"]))
    self.sequence().editFinished()
    return


def _setArtistByName(self, artistName):
    """ setArtistByName(artistName) -> sets the artist tag on a TrackItem by a given artistName string"""
    global gArtistList

    artist = self.getArtistFromName(artistName)
    if not artist:
        print((
            "Artist name: {} was not found in "
            "the gArtistList.").format(artistName))
        return

    # Do the update.
    self.updateArtistTag(artist)


def _setArtistByID(self, artistID):
    """ setArtistByID(artistID) -> sets the artist tag on a TrackItem by a given artistID integer"""
    global gArtistList

    artist = self.getArtistFromID(artistID)
    if not artist:
        print("Artist name: {} was not found in the gArtistList.".format(
            artistID))
        return

    # Do the update.
    self.updateArtistTag(artist)


# Inject status getter and setter methods into hiero.core.TrackItem
hiero.core.TrackItem.artist = _artist
hiero.core.TrackItem.setArtistByName = _setArtistByName
hiero.core.TrackItem.setArtistByID = _setArtistByID
hiero.core.TrackItem.getArtistFromName = _getArtistFromName
hiero.core.TrackItem.getArtistFromID = _getArtistFromID
hiero.core.TrackItem.updateArtistTag = _updateArtistTag


def _status(self):
    """status -> Returns the Shot status. None if no Status is set."""

    status = None
    tags = self.tags()
    for tag in tags:
        if tag.metadata().hasKey("tag.status"):
            status = tag.metadata().value("tag.status")
    return status


def _setStatus(self, status):
    """setShotStatus(status) -> Method to set the Status of a Shot.
  Adds a special kind of status Tag to a TrackItem
  Example: myTrackItem.setStatus("Final")

  @param status - a string, corresponding to the Status name
  """
    global gStatusTags

    # Get a valid Tag object from the Global list of statuses
    if not status in gStatusTags.keys():
        print("Status requested was not a valid Status string.")
        return

    # A shot should only have one status. Check if one exists and set accordingly
    statusTag = None
    tags = self.tags()
    for tag in tags:
        if tag.metadata().hasKey("tag.status"):
            statusTag = tag
            break

    if not statusTag:
        statusTag = hiero.core.Tag("Status")
        statusTag.setIcon(gStatusTags[status])
        statusTag.metadata().setValue("tag.status", status)
        self.addTag(statusTag)

    statusTag.setIcon(gStatusTags[status])
    statusTag.metadata().setValue("tag.status", status)

    self.sequence().editFinished()
    return


# Inject status getter and setter methods into hiero.core.TrackItem
hiero.core.TrackItem.setStatus = _setStatus
hiero.core.TrackItem.status = _status


# This is a convenience method for returning QActions with a triggered method based on the title string
def titleStringTriggeredAction(title, method, icon=None):
    action = QAction(title, None)
    action.setIcon(QIcon(icon))

    # We do this magic, so that the title string from the action is used to set the status
    def methodWrapper():
        method(title)

    action.triggered.connect(methodWrapper)
    return action


# Menu which adds a Set Status Menu to Timeline and Spreadsheet Views
class SetStatusMenu(QMenu):
    def __init__(self):
        QMenu.__init__(self, "Set Status", None)

        global gStatusTags
        self.statuses = gStatusTags
        self._statusActions = self.createStatusMenuActions()

        # Add the Actions to the Menu.
        for act in self.menuActions:
            self.addAction(act)

        hiero.core.events.registerInterest("kShowContextMenu/kTimeline",
                                           self.eventHandler)
        hiero.core.events.registerInterest("kShowContextMenu/kSpreadsheet",
                                           self.eventHandler)

    def createStatusMenuActions(self):
        self.menuActions = []
        for status in self.statuses:
            self.menuActions += [
                titleStringTriggeredAction(
                    status,
                    self.setStatusFromMenuSelection,
                    icon=gStatusTags[status])
            ]

    def setStatusFromMenuSelection(self, menuSelectionStatus):
        selectedShots = [
            item for item in self._selection
            if (isinstance(item, hiero.core.TrackItem))
        ]
        selectedTracks = [
            item for item in self._selection
            if (isinstance(item, (hiero.core.VideoTrack,
                                  hiero.core.AudioTrack)))
        ]

        # If we have a Track Header Selection, no shots could be selected, so create shotSelection list
        if len(selectedTracks) >= 1:
            for track in selectedTracks:
                selectedShots += [
                    item for item in track.items()
                    if (isinstance(item, hiero.core.TrackItem))
                ]

        # It's possible no shots exist on the Track, in which case nothing is required
        if len(selectedShots) == 0:
            return

        currentProject = selectedShots[0].project()

        with currentProject.beginUndo("Set Status"):
            # Shots selected
            for shot in selectedShots:
                shot.setStatus(menuSelectionStatus)

    # This handles events from the Project Bin View
    def eventHandler(self, event):
        if not hasattr(event.sender, "selection"):
            # Something has gone wrong, we should only be here if raised
            # by the Timeline/Spreadsheet view which gives a selection.
            return

        # Set the current selection
        self._selection = event.sender.selection()

        # Return if there's no Selection. We won't add the Menu.
        if len(self._selection) == 0:
            return

        event.menu.addMenu(self)


# Menu which adds a Set Status Menu to Timeline and Spreadsheet Views
class AssignArtistMenu(QMenu):
    def __init__(self):
        QMenu.__init__(self, "Assign Artist", None)

        global gArtistList
        self.artists = gArtistList
        self._artistsActions = self.createAssignArtistMenuActions()

        # Add the Actions to the Menu.
        for act in self.menuActions:
            self.addAction(act)

        hiero.core.events.registerInterest("kShowContextMenu/kTimeline",
                                           self.eventHandler)
        hiero.core.events.registerInterest("kShowContextMenu/kSpreadsheet",
                                           self.eventHandler)

    def createAssignArtistMenuActions(self):
        self.menuActions = []
        for artist in self.artists:
            self.menuActions += [
                titleStringTriggeredAction(
                    artist["artistName"],
                    self.setArtistFromMenuSelection,
                    icon=artist["artistIcon"])
            ]

    def setArtistFromMenuSelection(self, menuSelectionArtist):
        selectedShots = [
            item for item in self._selection
            if (isinstance(item, hiero.core.TrackItem))
        ]
        selectedTracks = [
            item for item in self._selection
            if (isinstance(item, (hiero.core.VideoTrack,
                                  hiero.core.AudioTrack)))
        ]

        # If we have a Track Header Selection, no shots could be selected, so create shotSelection list
        if len(selectedTracks) >= 1:
            for track in selectedTracks:
                selectedShots += [
                    item for item in track.items()
                    if (isinstance(item, hiero.core.TrackItem))
                ]

        # It's possible no shots exist on the Track, in which case nothing is required
        if len(selectedShots) == 0:
            return

        currentProject = selectedShots[0].project()

        with currentProject.beginUndo("Assign Artist"):
            # Shots selected
            for shot in selectedShots:
                shot.setArtistByName(menuSelectionArtist)

    # This handles events from the Project Bin View
    def eventHandler(self, event):
        if not hasattr(event.sender, "selection"):
            # Something has gone wrong, we should only be here if raised
            # by the Timeline/Spreadsheet view which gives a selection.
            return

        # Set the current selection
        self._selection = event.sender.selection()

        # Return if there's no Selection. We won't add the Menu.
        if len(self._selection) == 0:
            return

        event.menu.addMenu(self)


# Add the "Set Status" context menu to Timeline and Spreadsheet
if kAddStatusMenu:
    setStatusMenu = SetStatusMenu()

if kAssignArtistMenu:
    assignArtistMenu = AssignArtistMenu()

# Register our custom columns
hiero.ui.customColumn = CustomSpreadsheetColumns()
