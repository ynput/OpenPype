import sys
import time
import datetime
import signal
import threading

from ftrack_server import FtrackServer
import ftrack_api
from pype.api import Logger

log = Logger().get_logger("Event Server Legacy")


class TimerChecker(threading.Thread):
    max_time_out = 35

    def __init__(self, server, session):
        self.server = server
        self.session = session
        self.is_running = False
        self.failed = False
        super().__init__()

    def stop(self):
        self.is_running = False

    def run(self):
        start = datetime.datetime.now()
        self.is_running = True
        connected = False

        while True:
            if not self.is_running:
                break

            if not self.session.event_hub.connected:
                if not connected:
                    if (
                        (datetime.datetime.now() - start).seconds >
                        self.max_time_out
                    ):
                        log.error((
                            "Exiting event server. Session was not connected"
                            " to ftrack server in {} seconds."
                        ).format(self.max_time_out))
                        self.failed = True
                        break
                else:
                    log.error(
                        "Exiting event server. Event Hub is not connected."
                    )
                    self.server.stop_session()
                    self.failed = True
                    break
            else:
                if not connected:
                    connected = True

            time.sleep(1)


def main(args):
    check_thread = None
    try:
        server = FtrackServer("event")
        session = ftrack_api.Session(auto_connect_event_hub=True)

        check_thread = TimerChecker(server, session)
        check_thread.start()

        log.debug("Launching Ftrack Event Legacy Server")
        server.run_server(session)

    except Exception as exc:
        import traceback
        traceback.print_tb(exc.__traceback__)

    finally:
        log_info = True
        if check_thread is not None:
            check_thread.stop()
            check_thread.join()
            if check_thread.failed:
                log_info = False
        if log_info:
            log.info("Exiting Event server subprocess")
        return 1


if __name__ == "__main__":
    # Register interupt signal
    def signal_handler(sig, frame):
        print("You pressed Ctrl+C. Process ended.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    sys.exit(main(sys.argv))
