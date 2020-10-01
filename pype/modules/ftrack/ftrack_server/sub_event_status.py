import os
import sys
import json
import threading
import signal
import socket
import datetime

import ftrack_api
from ftrack_server import FtrackServer
from pype.modules.ftrack.ftrack_server.lib import (
    SocketSession, StatusEventHub,
    TOPIC_STATUS_SERVER, TOPIC_STATUS_SERVER_RESULT
)
from pype.api import Logger

log = Logger().get_logger("Event storer")
action_identifier = (
    "event.server.status" + os.environ["FTRACK_EVENT_SUB_ID"]
)
host_ip = socket.gethostbyname(socket.gethostname())
action_data = {
    "label": "Pype Admin",
    "variant": "- Event server Status ({})".format(host_ip),
    "description": "Get Infromation about event server",
    "actionIdentifier": action_identifier
}


class ObjectFactory:
    session = None
    status_factory = None
    checker_thread = None
    last_trigger = None


class Status:
    default_item = {
        "type": "label",
        "value": "Process info is not available at this moment."
    }

    def __init__(self, name, label, parent):
        self.name = name
        self.label = label or name
        self.parent = parent

        self.info = None
        self.last_update = None

    def update(self, info):
        self.last_update = datetime.datetime.now()
        self.info = info

    def get_delta_string(self, delta):
        days, hours, minutes = (
            delta.days, delta.seconds // 3600, delta.seconds // 60 % 60
        )
        delta_items = [
            "{}d".format(days),
            "{}h".format(hours),
            "{}m".format(minutes)
        ]
        if not days:
            delta_items.pop(0)
            if not hours:
                delta_items.pop(0)
                delta_items.append("{}s".format(delta.seconds % 60))
                if not minutes:
                    delta_items.pop(0)

        return " ".join(delta_items)

    def get_items(self):
        items = []
        last_update = "N/A"
        if self.last_update:
            delta = datetime.datetime.now() - self.last_update
            last_update = "{} ago".format(
                self.get_delta_string(delta)
            )

        last_update = "Updated: {}".format(last_update)
        items.append({
            "type": "label",
            "value": "#{}".format(self.label)
        })
        items.append({
            "type": "label",
            "value": "##{}".format(last_update)
        })

        if not self.info:
            if self.info is None:
                trigger_info_get()
            items.append(self.default_item)
            return items

        info = {}
        for key, value in self.info.items():
            if key not in ["created_at:", "created_at"]:
                info[key] = value
                continue

            datetime_value = datetime.datetime.strptime(
                value, "%Y.%m.%d %H:%M:%S"
            )
            delta = datetime.datetime.now() - datetime_value

            running_for = self.get_delta_string(delta)
            info["Started at"] = "{} [running: {}]".format(value, running_for)

        for key, value in info.items():
            items.append({
                "type": "label",
                "value": "<b>{}:</b> {}".format(key, value)
            })

        return items


class StatusFactory:

    note_item = {
        "type": "label",
        "value": (
            "<i>HINT: To refresh data uncheck"
            " all checkboxes and hit `Submit` button.</i>"
        )
    }
    splitter_item = {
        "type": "label",
        "value": "---"
    }

    def __init__(self, statuses={}):
        self.statuses = []
        for status in statuses.items():
            self.create_status(*status)

    def __getitem__(self, key):
        return self.get(key)

    def get(self, key, default=None):
        for status in self.statuses:
            if status.name == key:
                return status
        return default

    def is_filled(self):
        for status in self.statuses:
            if status.info is None:
                return False
        return True

    def create_status(self, name, label):
        new_status = Status(name, label, self)
        self.statuses.append(new_status)

    def process_event_result(self, event):
        subprocess_id = event["data"].get("subprocess_id")
        if subprocess_id != os.environ["FTRACK_EVENT_SUB_ID"]:
            return

        source = event["data"]["source"]
        data = event["data"]["status_info"]

        self.update_status_info(source, data)

    def update_status_info(self, process_name, info):
        for status in self.statuses:
            if status.name == process_name:
                status.update(info)
                break

    def bool_items(self):
        items = []
        items.append({
            "type": "label",
            "value": "#Restart process"
        })
        items.append({
            "type": "label",
            "value": (
                "<i><b>WARNING:</b> Main process may shut down when checked"
                " if does not run as a service!</i>"
            )
        })

        name_labels = {}
        for status in self.statuses:
            name_labels[status.name] = status.label

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
        items.extend(self.bool_items())

        for status in self.statuses:
            items.append(self.splitter_item)
            items.extend(status.get_items())

        return items


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


def server_activity(event):
    session = ObjectFactory.session
    if session is None:
        msg = "Session is not set. Can't trigger Reset action."
        log.warning(msg)
        return {
            "success": False,
            "message": msg
        }

    if not server_activity_validate_user(event):
        return {
            "success": False,
            "message": "You don't have permissions to see Event server status!"
        }

    values = event["data"].get("values") or {}
    is_checked = False
    for value in values.values():
        if value:
            is_checked = True
            break

    if not is_checked:
        return {
            "items": ObjectFactory.status_factory.items(),
            "title": "Server current status"
        }

    session = ObjectFactory.session
    if values["main"]:
        session.event_hub.sock.sendall(b"RestartM")
        return

    if values["storer"]:
        session.event_hub.sock.sendall(b"RestartS")

    if values["processor"]:
        session.event_hub.sock.sendall(b"RestartP")


def trigger_info_get():
    if ObjectFactory.last_trigger:
        delta = datetime.datetime.now() - ObjectFactory.last_trigger
        if delta.seconds() < 5:
            return

    session = ObjectFactory.session
    session.event_hub.publish(
        ftrack_api.event.base.Event(
            topic=TOPIC_STATUS_SERVER,
            data={"subprocess_id": os.environ["FTRACK_EVENT_SUB_ID"]}
        ),
        on_error="ignore"
    )


def on_start(event):
    session = ObjectFactory.session
    source_id = event.get("source", {}).get("id")
    if not source_id or source_id != session.event_hub.id:
        return

    if session is None:
        log.warning("Session is not set. Can't trigger Sync to avalon action.")
        return True
    trigger_info_get()


def register(session):
    '''Registers the event, subscribing the discover and launch topics.'''
    session.event_hub.subscribe(
        "topic=ftrack.action.discover",
        server_activity_discover
    )
    session.event_hub.subscribe("topic=pype.status.started", on_start)

    status_launch_subscription = (
        "topic=ftrack.action.launch and data.actionIdentifier={}"
    ).format(action_identifier)

    session.event_hub.subscribe(
        status_launch_subscription,
        server_activity
    )

    session.event_hub.subscribe(
        "topic={}".format(TOPIC_STATUS_SERVER_RESULT),
        ObjectFactory.status_factory.process_event_result
    )


def heartbeat():
    if ObjectFactory.status_factory.is_filled():
        return

    trigger_info_get()


def main(args):
    port = int(args[-1])
    server_info = json.loads(args[-2])

    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect the socket to the port where the server is listening
    server_address = ("localhost", port)
    log.debug("Statuser connected to {} port {}".format(*server_address))
    sock.connect(server_address)
    sock.sendall(b"CreatedStatus")
    # store socket connection object
    ObjectFactory.sock = sock

    ObjectFactory.status_factory["main"].update(server_info)
    _returncode = 0
    try:
        session = SocketSession(
            auto_connect_event_hub=True, sock=sock, Eventhub=StatusEventHub
        )
        ObjectFactory.session = session
        session.event_hub.heartbeat_callbacks.append(heartbeat)
        register(session)
        server = FtrackServer("event")
        log.debug("Launched Ftrack Event statuser")

        server.run_server(session, load_files=False)

    except Exception:
        _returncode = 1
        log.error("ServerInfo subprocess crashed", exc_info=True)

    finally:
        log.debug("Ending. Closing socket.")
        sock.close()
        return _returncode


class OutputChecker(threading.Thread):
    read_input = True

    def run(self):
        while self.read_input:
            for line in sys.stdin:
                line = line.rstrip().lower()
                if not line.startswith("reset:"):
                    continue
                process_name = line.replace("reset:", "")

                ObjectFactory.status_factory.update_status_info(
                    process_name, None
                )

    def stop(self):
        self.read_input = False


if __name__ == "__main__":
    # Register interupt signal
    def signal_handler(sig, frame):
        print("You pressed Ctrl+C. Process ended.")
        ObjectFactory.checker_thread.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    statuse_names = {
        "main": "Main process",
        "storer": "Event Storer",
        "processor": "Event Processor"
    }
    ObjectFactory.status_factory = StatusFactory(statuse_names)

    checker_thread = OutputChecker()
    ObjectFactory.checker_thread = checker_thread
    checker_thread.start()

    sys.exit(main(sys.argv))
