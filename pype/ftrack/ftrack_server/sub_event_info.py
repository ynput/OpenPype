import os
import sys
import copy
import signal
import socket
import uuid
from datetime import datetime

import ftrack_api
from ftrack_server import FtrackServer
from pype.ftrack.ftrack_server.lib import (
    SocketSession, SocketBaseEventHub,
    TOPIC_STATUS_SERVER, TOPIC_STATUS_SERVER_RESULT
)
from pypeapp import Logger

log = Logger().get_logger("Event storer")
log.info(os.environ.get("FTRACK_EVENT_SUB_ID"))


class ObjectFactory:
    session = None
    sock = None
    subprocess_id = os.environ["FTRACK_EVENT_SUB_ID"]
    status_factory = None


def trigger_status_info(status_id=None, status=None):
    if not status and not status_id:
        log.warning(
            "`status_id` or `status` must be specified to trigger action."
        )
        return

    if not status:
        status = ObjectFactory.status_factory[status_id]

    if not status:
        return

    new_event_data = copy.deepcopy(action_data)
    new_event_data.update({
        "selection": []
    })
    new_event_data["subprocess_id"] = ObjectFactory.subprocess_id
    new_event_data["status_id"] = status.id

    new_event = ftrack_api.event.base.Event(
        topic="ftrack.action.launch",
        data=new_event_data,
        source=status.source
    )
    ObjectFactory.session.event_hub.publish(new_event)


action_identifier = (
    "event.server.status" + ObjectFactory.subprocess_id
)

# TODO add IP adress to label
# TODO add icon
action_data = {
    "label": "Pype Admin",
    "variant": "Event server Status",
    "description": "Get Infromation about event server",
    "actionIdentifier": action_identifier,
    "icon": None
}


class Status:
    default_item = {
        "type": "label",
        "value": "Information not allowed."
    }
    note_item = {
        "type": "label",
        "value": "Hit `submit` to refresh data."
    }
    splitter_item = {
        "type": "label",
        "value": "---"
    }

    def __init__(self, source_info, parent):
        self.id = str(uuid.uuid1())
        self.created = datetime.now()
        self.parent = parent

        self.source = source_info

        self.main_process = None
        self.storer = None
        self.processor = None

    def add_result(self, source, data):
        if source.lower() == "storer":
            self.storer = data

        elif source.lower() == "processor":
            self.processor = data

        else:
            self.main_process = data

    def filled(self):
        # WARNING DEBUG PART!!!!
        return True
        return (
            self.main_process is not None and
            self.storer is not None and
            self.processor is not None
        )

    def get_items_from_dict(self, in_dict):
        items = []
        for key, value in in_dict.items():
            items.append({
                "type": "label",
                "value": "##{}".format(key)
            })
            items.append({
                "type": "label",
                "value": value
            })
        return items

    def bool_items(self):
        items = []
        name_labels = {
            "shutdown_main": "Shutdown main process",
            "reset_storer": "Reset storer",
            "reset_processor": "Reset processor"
        }
        for name, label in name_labels.items():
            items.append({
                "type": "boolean",
                "value": False,
                "label": label,
                "name": name
            })
        return items

    def items(self):
        items = []
        items.append(self.note_item)

        items.append({"type": "label", "value": "Main process"})
        if not self.main_process:
            items.append(self.default_item)
        else:
            items.extend(
                self.get_items_from_dict(self.main_process)
            )

        items.append(self.splitter_item)
        items.append({"type": "label", "value": "Storer process"})
        if not self.storer:
            items.append(self.default_item)
        else:
            items.extend(
                self.get_items_from_dict(self.storer)
            )

        items.append(self.splitter_item)
        items.append({"type": "label", "value": "Processor process"})
        if not self.processor:
            items.append(self.default_item)
        else:
            items.extend(
                self.get_items_from_dict(self.processor)
            )

        items.append(self.splitter_item)
        items.extend(self.bool_items())

        return items

    @property
    def is_overtime(self):
        time_delta = (datetime.now() - self.created).total_seconds()
        return time_delta >= self.parent.max_delta_seconds


class StatusFactory:
    max_delta_seconds = 30

    def __init__(self):
        self.statuses = {}

    def __getitem__(self, key):
        return self.statuses.get(key)

    def create_status(self, source_info):
        new_status = Status(source_info, self)
        self.statuses[new_status.id] = new_status
        return new_status

    def process_result(self, event):
        subprocess_id = event["data"].get("subprocess_id")
        if subprocess_id != ObjectFactory.subprocess_id:
            return

        status_id = event["data"].get("status_id")
        status = self.statuses[status_id]
        if not status:
            return

        source = event["data"]["source"]
        data = event["data"]["status_info"]

        status.add_result(source, data)
        if status.filled():
            trigger_status_info(status=status)


def server_activity_validate_user(event):
    """Validate user permissions to show server info."""
    session = ObjectFactory.session

    username = event["source"].get("user", {}).get("username")
    if not username:
        return False

    user_ent = session.query(
        "User where username = \"{}\"".format(username)
    ).first()
    if not user_ent:
        return False

    role_list = ["Pypeclub", "Administrator"]
    for role in user_ent["user_security_roles"]:
        if role["security_role"]["name"] in role_list:
            return True
    return False


def server_activity_discover(event):
    """Discover action in actions menu conditions."""
    session = ObjectFactory.session
    if session is None:
        return

    if not server_activity_validate_user(event):
        return

    return {"items": [action_data]}


def handle_filled_event(event):
    subprocess_id = event["data"].get("subprocess_id")
    if subprocess_id != ObjectFactory.subprocess_id:
        return None

    status_id = event["data"].get("status_id")
    status = ObjectFactory.status_factory[status_id]
    if not status:
        return None

    values = event.get("values")
    if values:
        log.info(values)

    title = "Event server - Status"

    event_data = copy.deepcopy(event["data"])
    event_data.update({
        "type": "widget",
        "items": status.items(),
        "title": title
    })

    ObjectFactory.session.event_hub.publish(
        ftrack_api.event.base.Event(
            topic="ftrack.action.trigger-user-interface",
            data=event_data
        ),
        on_error='ignore'
    )


def server_activity(event):
    session = ObjectFactory.session
    if session is None:
        msg = "Session is not set. Can't trigger Reset action."
        log.warning(msg)
        return {
            "success": False,
            "message": msg
        }

    valid = server_activity_validate_user(event)
    if not valid:
        return {
            "success": False,
            "message": "You don't have permissions to see Event server status!"
        }

    subprocess_id = event["data"].get("subprocess_id")
    if subprocess_id is not None:
        return handle_filled_event(event)

    status = ObjectFactory.status_factory.create_status(event["source"])

    event_data = {
        "status_id": status.id,
        "subprocess_id": ObjectFactory.subprocess_id
    }
    session.event_hub.publish(
        ftrack_api.event.base.Event(
            topic=TOPIC_STATUS_SERVER,
            data=event_data
        ),
        on_error="ignore"
    )

    return {
        "success": True,
        "message": "Collecting information (this may take > 20s)"
    }


def register(session):
    '''Registers the event, subscribing the discover and launch topics.'''
    session.event_hub.subscribe(
        "topic=ftrack.action.discover",
        server_activity_discover
    )

    status_launch_subscription = (
        "topic=ftrack.action.launch and data.actionIdentifier={}"
    ).format(action_identifier)

    session.event_hub.subscribe(
        status_launch_subscription,
        server_activity
    )

    session.event_hub.subscribe(
        "topic={}".format(TOPIC_STATUS_SERVER_RESULT),
        ObjectFactory.status_factory.process_result
    )


def main(args):
    port = int(args[-1])

    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect the socket to the port where the server is listening
    server_address = ("localhost", port)
    log.debug("Storer connected to {} port {}".format(*server_address))
    sock.connect(server_address)
    sock.sendall(b"CreatedStatus")
    # store socket connection object
    ObjectFactory.sock = sock
    ObjectFactory.status_factory = StatusFactory()

    _returncode = 0
    try:
        session = SocketSession(
            auto_connect_event_hub=True, sock=sock, Eventhub=SocketBaseEventHub
        )
        ObjectFactory.session = session
        register(session)
        server = FtrackServer("event")
        log.debug("Launched Ftrack Event storer")
        server.run_server(session, load_files=False)

    except Exception:
        _returncode = 1
        log.error("ServerInfo subprocess crashed", exc_info=True)

    finally:
        log.debug("Ending. Closing socket.")
        sock.close()
        return _returncode


if __name__ == "__main__":
    # Register interupt signal
    def signal_handler(sig, frame):
        print("You pressed Ctrl+C. Process ended.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    sys.exit(main(sys.argv))


example_action_event = {
    'data': {
        'selection': [],
        'description': 'Test action2',
        'variant': None,
        'label': 'Test action2',
        'actionIdentifier': 'test.action2.3ceffe5e9acf40f8aa80603adebd0d06',
        'values': {},
        'icon': None,
    },
    'topic': 'ftrack.action.launch',
    'sent': None,
    'source': {
        'id': 'eb67d186301c4cbbab73c1aee9b7c55d',
        'user': {'username': 'jakub.trllo', 'id': '2a8ae090-cbd3-11e8-a87a-0a580aa00121'}
    },
    'target': '',
    'in_reply_to_event': None
}
