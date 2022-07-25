import os
import hiero.core.events
from openpype.api import Logger
from openpype.lib import register_event_callback
from .lib import (
    sync_avalon_data_to_workfile,
    launch_workfiles_app,
    selection_changed_timeline,
    before_project_save,
)
from .tags import add_tags_to_workfile
from .menu import update_menu_task_label

log = Logger().get_logger(__name__)


def startupCompleted(event):
    log.info("startup competed event...")
    return


def shutDown(event):
    log.info("shut down event...")
    return


def beforeNewProjectCreated(event):
    log.info("before new project created event...")
    return


def afterNewProjectCreated(event):
    log.info("after new project created event...")
    # sync avalon data to project properties
    sync_avalon_data_to_workfile()

    # add tags from preset
    add_tags_to_workfile()

    # Workfiles.
    if int(os.environ.get("WORKFILES_STARTUP", "0")):
        hiero.core.events.sendEvent("kStartWorkfiles", None)
        # reset workfiles startup not to open any more in session
        os.environ["WORKFILES_STARTUP"] = "0"


def beforeProjectLoad(event):
    log.info("before project load event...")
    return


def afterProjectLoad(event):
    log.info("after project load event...")
    # sync avalon data to project properties
    sync_avalon_data_to_workfile()

    # add tags from preset
    add_tags_to_workfile()


def beforeProjectClosed(event):
    log.info("before project closed event...")
    return


def afterProjectClosed(event):
    log.info("after project closed event...")
    return


def beforeProjectSaved(event):
    log.info("before project saved event...")
    return


def afterProjectSaved(event):
    log.info("after project saved event...")
    return


def register_hiero_events():
    log.info(
        "Registering events for: kBeforeNewProjectCreated, "
        "kAfterNewProjectCreated, kBeforeProjectLoad, kAfterProjectLoad, "
        "kBeforeProjectSave, kAfterProjectSave, kBeforeProjectClose, "
        "kAfterProjectClose, kShutdown, kStartup, kSelectionChanged"
    )

    # hiero.core.events.registerInterest(
    #     "kBeforeNewProjectCreated", beforeNewProjectCreated)
    hiero.core.events.registerInterest(
        "kAfterNewProjectCreated", afterNewProjectCreated)

    # hiero.core.events.registerInterest(
    #     "kBeforeProjectLoad", beforeProjectLoad)
    hiero.core.events.registerInterest(
        "kAfterProjectLoad", afterProjectLoad)

    hiero.core.events.registerInterest(
        "kBeforeProjectSave", before_project_save)
    # hiero.core.events.registerInterest(
    #     "kAfterProjectSave", afterProjectSaved)
    #
    # hiero.core.events.registerInterest(
    #     "kBeforeProjectClose", beforeProjectClosed)
    # hiero.core.events.registerInterest(
    #     "kAfterProjectClose", afterProjectClosed)
    #
    # hiero.core.events.registerInterest("kShutdown", shutDown)
    # hiero.core.events.registerInterest("kStartup", startupCompleted)

    # INFO: was disabled because it was slowing down timeline operations
    # hiero.core.events.registerInterest(
    #     ("kSelectionChanged", "kTimeline"), selection_changed_timeline)

    # workfiles
    try:
        hiero.core.events.registerEventType("kStartWorkfiles")
        hiero.core.events.registerInterest(
            "kStartWorkfiles", launch_workfiles_app)
    except RuntimeError:
        pass

def register_events():
    """
    Adding all callbacks.
    """

    # if task changed then change notext of hiero
    register_event_callback("taskChanged", update_menu_task_label)
    log.info("Installed event callback for 'taskChanged'..")
