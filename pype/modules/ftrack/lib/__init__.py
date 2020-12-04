import os
from . import avalon_sync
from . import credentials
from .ftrack_base_handler import BaseHandler
from .ftrack_event_handler import BaseEvent
from .ftrack_action_handler import BaseAction, ServerAction, statics_icon

FTRACK_MODULE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_HANDLERS_DIR = os.path.join(
    FTRACK_MODULE_DIR,
    "events"
)
USER_HANDLERS_DIR = os.path.join(
    FTRACK_MODULE_DIR,
    "actions"
)

__all__ = (
    "avalon_sync",
    "credentials",
    "BaseHandler",
    "BaseEvent",
    "BaseAction",
    "ServerAction",
    "statics_icon",
    "FTRACK_MODULE_DIR",
    "SERVER_HANDLERS_DIR",
    "USER_HANDLERS_DIR"
)
