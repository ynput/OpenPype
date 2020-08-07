import os
import sys
import datetime
import signal
import socket
import pymongo

import ftrack_api
from ftrack_server import FtrackServer
from pype.modules.ftrack.ftrack_server.lib import (
    SocketSession, StorerEventHub,
    get_ftrack_event_mongo_info,
    TOPIC_STATUS_SERVER, TOPIC_STATUS_SERVER_RESULT
)
from pype.modules.ftrack.lib.custom_db_connector import CustomDbConnector
from pype.api import Logger

log = Logger().get_logger("Event storer")
subprocess_started = datetime.datetime.now()


class SessionFactory:
    session = None


uri, port, database, table_name = get_ftrack_event_mongo_info()
dbcon = CustomDbConnector(uri, database, port, table_name)

# ignore_topics = ["ftrack.meta.connected"]
ignore_topics = []


def install_db():
    try:
        dbcon.install()
        dbcon._database.list_collection_names()
    except pymongo.errors.AutoReconnect:
        log.error("Mongo server \"{}\" is not responding, exiting.".format(
            os.environ["AVALON_MONGO"]
        ))
        sys.exit(0)


def launch(event):
    if event.get("topic") in ignore_topics:
        return

    event_data = event._data
    event_id = event["id"]

    event_data["pype_data"] = {
        "stored": datetime.datetime.utcnow(),
        "is_processed": False
    }

    try:
        # dbcon.insert_one(event_data)
        dbcon.replace_one({"id": event_id}, event_data, upsert=True)
        log.debug("Event: {} stored".format(event_id))

    except pymongo.errors.AutoReconnect:
        log.error("Mongo server \"{}\" is not responding, exiting.".format(
            os.environ["AVALON_MONGO"]
        ))
        sys.exit(0)

    except Exception as exc:
        log.error(
            "Event: {} failed to store".format(event_id),
            exc_info=True
        )


def trigger_sync(event):
    session = SessionFactory.session
    source_id = event.get("source", {}).get("id")
    if not source_id or source_id != session.event_hub.id:
        return

    if session is None:
        log.warning("Session is not set. Can't trigger Sync to avalon action.")
        return True

    projects = session.query("Project").all()
    if not projects:
        return True

    query = {
        "pype_data.is_processed": False,
        "topic": "ftrack.action.launch",
        "data.actionIdentifier": "sync.to.avalon.server"
    }
    set_dict = {
        "$set": {"pype_data.is_processed": True}
    }
    dbcon.update_many(query, set_dict)

    selections = []
    for project in projects:
        if project["status"] != "active":
            continue

        auto_sync = project["custom_attributes"].get("avalon_auto_sync")
        if not auto_sync:
            continue

        selections.append({
            "entityId": project["id"],
            "entityType": "show"
        })

    if not selections:
        return

    user = session.query(
        "User where username is \"{}\"".format(session.api_user)
    ).one()
    user_data = {
        "username": user["username"],
        "id": user["id"]
    }

    for selection in selections:
        event_data = {
            "actionIdentifier": "sync.to.avalon.server",
            "selection": [selection]
        }
        session.event_hub.publish(
            ftrack_api.event.base.Event(
                topic="ftrack.action.launch",
                data=event_data,
                source=dict(user=user_data)
            ),
            on_error="ignore"
        )


def send_status(event):
    session = SessionFactory.session
    if not session:
        return

    subprocess_id = event["data"].get("subprocess_id")
    if not subprocess_id:
        return

    if subprocess_id != os.environ["FTRACK_EVENT_SUB_ID"]:
        return

    new_event_data = {
        "subprocess_id": os.environ["FTRACK_EVENT_SUB_ID"],
        "source": "storer",
        "status_info": {
            "created_at": subprocess_started.strftime("%Y.%m.%d %H:%M:%S")
        }
    }

    new_event = ftrack_api.event.base.Event(
        topic=TOPIC_STATUS_SERVER_RESULT,
        data=new_event_data
    )

    session.event_hub.publish(new_event)


def register(session):
    '''Registers the event, subscribing the discover and launch topics.'''
    install_db()
    session.event_hub.subscribe("topic=*", launch)
    session.event_hub.subscribe("topic=pype.storer.started", trigger_sync)
    session.event_hub.subscribe(
        "topic={}".format(TOPIC_STATUS_SERVER), send_status
    )


def main(args):
    port = int(args[-1])

    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect the socket to the port where the server is listening
    server_address = ("localhost", port)
    log.debug("Storer connected to {} port {}".format(*server_address))
    sock.connect(server_address)
    sock.sendall(b"CreatedStore")

    try:
        session = SocketSession(
            auto_connect_event_hub=True, sock=sock, Eventhub=StorerEventHub
        )
        SessionFactory.session = session
        register(session)
        server = FtrackServer("event")
        log.debug("Launched Ftrack Event storer")
        server.run_server(session, load_files=False)

    except pymongo.errors.OperationFailure:
        log.error((
            "Error with Mongo access, probably permissions."
            "Check if exist database with name \"{}\""
            " and collection \"{}\" inside."
        ).format(database, table_name))
        sock.sendall(b"MongoError")

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
