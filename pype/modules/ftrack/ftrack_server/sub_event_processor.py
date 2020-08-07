import os
import sys
import signal
import socket
import datetime

from ftrack_server import FtrackServer
from pype.modules.ftrack.ftrack_server.lib import (
    SocketSession, ProcessEventHub, TOPIC_STATUS_SERVER
)
import ftrack_api
from pype.api import Logger, config

log = Logger().get_logger("Event processor")

subprocess_started = datetime.datetime.now()


class SessionFactory:
    session = None


def send_status(event):
    subprocess_id = event["data"].get("subprocess_id")
    if not subprocess_id:
        return

    if subprocess_id != os.environ["FTRACK_EVENT_SUB_ID"]:
        return

    session = SessionFactory.session
    if not session:
        return

    new_event_data = {
        "subprocess_id": subprocess_id,
        "source": "processor",
        "status_info": {
            "created_at": subprocess_started.strftime("%Y.%m.%d %H:%M:%S")
        }
    }

    new_event = ftrack_api.event.base.Event(
        topic="pype.event.server.status.result",
        data=new_event_data
    )

    session.event_hub.publish(new_event)


def register(session):
    '''Registers the event, subscribing the discover and launch topics.'''
    session.event_hub.subscribe(
        "topic={}".format(TOPIC_STATUS_SERVER), send_status
    )


def clockify_module_registration():
    module_name = "Clockify"

    menu_items = config.get_presets()["tray"]["menu_items"]
    if not menu_items["item_usage"][module_name]:
        return

    api_key = os.environ.get("CLOCKIFY_API_KEY")
    if not api_key:
        log.warning("Clockify API key is not set.")
        return

    workspace_name = os.environ.get("CLOCKIFY_WORKSPACE")
    if not workspace_name:
        workspace_name = (
            menu_items
            .get("attributes", {})
            .get(module_name, {})
            .get("workspace_name", {})
        )

    if not workspace_name:
        log.warning("Clockify Workspace is not set.")
        return

    os.environ["CLOCKIFY_WORKSPACE"] = workspace_name

    from pype.modules.clockify.constants import CLOCKIFY_FTRACK_SERVER_PATH

    current = os.environ.get("FTRACK_EVENTS_PATH") or ""
    if current:
        current += os.pathsep
    os.environ["FTRACK_EVENTS_PATH"] = current + CLOCKIFY_FTRACK_SERVER_PATH
    return True


def main(args):
    port = int(args[-1])
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect the socket to the port where the server is listening
    server_address = ("localhost", port)
    log.debug("Processor connected to {} port {}".format(*server_address))
    sock.connect(server_address)

    sock.sendall(b"CreatedProcess")
    try:
        clockify_module_registration()
    except Exception:
        log.info("Clockify registration failed.", exc_info=True)

    try:
        session = SocketSession(
            auto_connect_event_hub=True, sock=sock, Eventhub=ProcessEventHub
        )
        register(session)
        SessionFactory.session = session

        server = FtrackServer("event")
        log.debug("Launched Ftrack Event processor")
        server.run_server(session)

    except Exception:
        log.error("Event server crashed. See traceback below", exc_info=True)

    finally:
        log.debug("First closing socket")
        sock.close()
        return 1


if __name__ == "__main__":
    # Register interupt signal
    def signal_handler(sig, frame):
        print("You pressed Ctrl+C. Process ended.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    sys.exit(main(sys.argv))
