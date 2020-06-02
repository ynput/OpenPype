import os
import hiero.core.events
from pype.api import Logger
from .lib import sync_avalon_data_to_workfile, launch_workfiles_app
from .tags import add_tags_from_presets

log = Logger().get_logger(__name__, "nukestudio")


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
    # sync avalon data to project properities
    sync_avalon_data_to_workfile()

    # add tags from preset
    add_tags_from_presets()

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
    # sync avalon data to project properities
    sync_avalon_data_to_workfile()

    # add tags from preset
    add_tags_from_presets()


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
        "kAfterProjectClose, kShutdown, kStartup"
        )

    # hiero.core.events.registerInterest(
    #     "kBeforeNewProjectCreated", beforeNewProjectCreated)
    hiero.core.events.registerInterest(
        "kAfterNewProjectCreated", afterNewProjectCreated)

    # hiero.core.events.registerInterest(
    #     "kBeforeProjectLoad", beforeProjectLoad)
    hiero.core.events.registerInterest(
        "kAfterProjectLoad", afterProjectLoad)

    # hiero.core.events.registerInterest(
    #     "kBeforeProjectSave", beforeProjectSaved)
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

    # workfiles
    hiero.core.events.registerEventType("kStartWorkfiles")
    hiero.core.events.registerInterest("kStartWorkfiles", launch_workfiles_app)
