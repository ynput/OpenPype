try:
    from PySide.QtGui import *
    from PySide.QtCore import *
except:
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
    from PySide2.QtCore import *

from hiero.core.util import uniquify, version_get, version_set
import hiero.core
import hiero.ui
import nuke

# A globally variable for storing the current Project
gTrackedActiveProject = None

# This selection handler will track changes in items selected/deselected in the Bin/Timeline/Spreadsheet Views


def __trackActiveProjectHandler(event):
    global gTrackedActiveProject
    selection = event.sender.selection()
    binSelection = selection
    if len(binSelection) > 0 and hasattr(binSelection[0], "project"):
        proj = binSelection[0].project()

        # We only store this if its a valid, active User Project
        if proj in hiero.core.projects(hiero.core.Project.kUserProjects):
            gTrackedActiveProject = proj


hiero.core.events.registerInterest(
    "kSelectionChanged/kBin", __trackActiveProjectHandler)
hiero.core.events.registerInterest(
    "kSelectionChanged/kTimeline", __trackActiveProjectHandler)
hiero.core.events.registerInterest(
    "kSelectionChanged/Spreadsheet", __trackActiveProjectHandler)


def activeProject():
    """hiero.ui.activeProject() -> returns the current Project

    Note: There is not technically a notion of a "active" Project in Hiero/NukeStudio, as it is a multi-project App.
    This method determines what is "active" by going down the following rules...

    # 1 - If the current Viewer (hiero.ui.currentViewer) contains a Clip or Sequence, this item is assumed to give the active Project
    # 2 - If nothing is currently in the Viewer, look to the active View, determine project from active selection
    # 3 - If no current selection can be determined, fall back to a globally tracked last selection from trackActiveProjectHandler
    # 4 - If all those rules fail, fall back to the last project in the list of hiero.core.projects()

    @return: hiero.core.Project"""
    global gTrackedActiveProject
    activeProject = None

    # Case 1 : Look for what the current Viewr tells us - this might not be what we want, and relies on hiero.ui.currentViewer() being robust.
    cv = hiero.ui.currentViewer().player().sequence()
    if hasattr(cv, "project"):
        activeProject = cv.project()
    else:
        # Case 2: We can't determine a project from the current Viewer, so try seeing what's selected in the activeView
        # Note that currently, if you run activeProject from the Script Editor, the activeView is always None, so this will rarely get used!
        activeView = hiero.ui.activeView()
        if activeView:
            # We can determine an active View.. see what's being worked with
            selection = activeView.selection()

            # Handle the case where nothing is selected in the active view
            if len(selection) == 0:
                # It's possible that there is no selection in a Timeline/Spreadsheet, but these views have "sequence" method, so try that...
                if isinstance(hiero.ui.activeView(), (hiero.ui.TimelineEditor, hiero.ui.SpreadsheetView)):
                    activeSequence = activeView.sequence()
                    if hasattr(currentItem, "project"):
                        activeProject = activeSequence.project()

            # The active view has a selection... assume that the first item in the selection has the active Project
            else:
                currentItem = selection[0]
                if hasattr(currentItem, "project"):
                    activeProject = currentItem.project()

    # Finally, Cases 3 and 4...
    if not activeProject:
        activeProjects = hiero.core.projects(hiero.core.Project.kUserProjects)
        if gTrackedActiveProject in activeProjects:
            activeProject = gTrackedActiveProject
        else:
            activeProject = activeProjects[-1]

    return activeProject

# Method to get all recent projects


def recentProjects():
    """hiero.core.recentProjects() -> Returns a list of paths to recently opened projects

    Hiero stores up to 5 recent projects in uistate.ini with the [recentFile]/# key.

    @return: list of paths to .hrox Projects"""

    appSettings = hiero.core.ApplicationSettings()
    recentProjects = []
    for i in range(0, 5):
        proj = appSettings.value('recentFile/%i' % i)
        if len(proj) > 0:
            recentProjects.append(proj)
    return recentProjects

# Method to get recent project by index


def recentProject(k=0):
    """hiero.core.recentProject(k) -> Returns the recent project path, specified by integer k (0-4)

    @param: k (optional, default = 0) - an integer from 0-4, relating to the index of recent projects.

    @return: hiero.core.Project"""

    appSettings = hiero.core.ApplicationSettings()
    proj = appSettings.value('recentFile/%i' % int(k), None)
    return proj

# Method to get open project by index


def openRecentProject(k=0):
    """hiero.core.openRecentProject(k) -> Opens the most the recent project as listed in the Open Recent list.

    @param: k (optional, default = 0) - an integer from 0-4, relating to the index of recent projects.
    @return: hiero.core.Project"""

    appSettings = hiero.core.ApplicationSettings()
    proj = appSettings.value('recentFile/%i' % int(k), None)
    proj = hiero.core.openProject(proj)
    return proj


# Duck punch these methods into the relevant ui/core namespaces
hiero.ui.activeProject = activeProject
hiero.core.recentProjects = recentProjects
hiero.core.recentProject = recentProject
hiero.core.openRecentProject = openRecentProject


# Method to Save a new Version of the activeHrox Project
class SaveAllProjects(QAction):

    def __init__(self):
        QAction.__init__(self, "Save All Projects", None)
        self.triggered.connect(self.projectSaveAll)
        hiero.core.events.registerInterest(
            "kShowContextMenu/kBin", self.eventHandler)

    def projectSaveAll(self):
        allProjects = hiero.core.projects()
        for proj in allProjects:
            try:
                proj.save()
                print("Saved Project: {} to: {} ".format(
                    proj.name(), proj.path()
                ))
            except:
                print((
                    "Unable to save Project: {} to: {}. "
                    "Check file permissions.").format(
                        proj.name(), proj.path()))

    def eventHandler(self, event):
        event.menu.addAction(self)

# For projects with v# in the path name, saves out a new Project with v#+1


class SaveNewProjectVersion(QAction):

    def __init__(self):
        QAction.__init__(self, "Save New Version...", None)
        self.triggered.connect(self.saveNewVersion)
        hiero.core.events.registerInterest(
            "kShowContextMenu/kBin", self.eventHandler)
        self.selectedProjects = []

    def saveNewVersion(self):
        if len(self.selectedProjects) > 0:
            projects = self.selectedProjects
        else:
            projects = [hiero.ui.activeProject()]

        if len(projects) < 1:
            return

        for proj in projects:
            oldName = proj.name()
            path = proj.path()
            v = None
            prefix = None
            try:
                (prefix, v) = version_get(path, "v")
            except ValueError as msg:
                print(msg)

            if (prefix is not None) and (v is not None):
                v = int(v)
                newPath = version_set(path, prefix, v, v + 1)
                try:
                    proj.saveAs(newPath)
                    print("Saved new project version: {} to: {} ".format(
                        oldName, newPath))
                except:
                    print((
                        "Unable to save Project: {}. Check file permissions."
                    ).format(oldName))
            else:
                newPath = path.replace(".hrox", "_v01.hrox")
                answer = nuke.ask(
                    "%s does not contain a version number.\nDo you want to save as %s?" % (proj, newPath))
                if answer:
                    try:
                        proj.saveAs(newPath)
                        print("Saved new project version: {} to: {} ".format(
                            oldName, newPath))
                    except:
                        print((
                            "Unable to save Project: {}. Check file "
                            "permissions.").format(oldName))

    def eventHandler(self, event):
        self.selectedProjects = []
        if hasattr(event.sender, "selection") and event.sender.selection() is not None and len(event.sender.selection()) != 0:
            selection = event.sender.selection()
            self.selectedProjects = uniquify(
                [item.project() for item in selection])
            event.menu.addAction(self)


# Instantiate the actions
saveAllAct = SaveAllProjects()
saveNewAct = SaveNewProjectVersion()

fileMenu = hiero.ui.findMenuAction("foundry.menu.file")
importAct = hiero.ui.findMenuAction("foundry.project.importFiles")
hiero.ui.insertMenuAction(saveNewAct, fileMenu.menu(),
                          before="Import File(s)...")
hiero.ui.insertMenuAction(saveAllAct, fileMenu.menu(),
                          before="Import File(s)...")
fileMenu.menu().insertSeparator(importAct)
