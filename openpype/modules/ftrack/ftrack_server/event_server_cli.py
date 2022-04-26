import os
import sys
import signal
import datetime
import subprocess
import socket
import json
import platform
import getpass
import atexit
import time
import uuid

import ftrack_api
import pymongo
from openpype.lib import (
    get_openpype_execute_args,
    OpenPypeMongoConnection,
    get_openpype_version,
    get_build_version,
    validate_mongo_connection
)
from openpype_modules.ftrack import FTRACK_MODULE_DIR
from openpype_modules.ftrack.lib import credentials
from openpype_modules.ftrack.ftrack_server.lib import check_ftrack_url
from openpype_modules.ftrack.ftrack_server import socket_thread


class MongoPermissionsError(Exception):
    """Is used when is created multiple objects of same RestApi class."""
    def __init__(self, message=None):
        if not message:
            message = "Exiting because have issue with acces to MongoDB"
        super().__init__(message)


def check_mongo_url(mongo_uri, log_error=False):
    """Checks if mongo server is responding"""
    try:
        validate_mongo_connection(mongo_uri)

    except pymongo.errors.InvalidURI as err:
        if log_error:
            print("Can't connect to MongoDB at {} because: {}".format(
                mongo_uri, err
            ))
        return False

    except pymongo.errors.ServerSelectionTimeoutError as err:
        if log_error:
            print("Can't connect to MongoDB at {} because: {}".format(
                mongo_uri, err
            ))
        return False

    return True


def validate_credentials(url, user, api):
    first_validation = True
    if not user:
        print('- Ftrack Username is not set')
        first_validation = False
    if not api:
        print('- Ftrack API key is not set')
        first_validation = False
    if not first_validation:
        return False

    try:
        session = ftrack_api.Session(
            server_url=url,
            api_user=user,
            api_key=api
        )
        session.close()
    except Exception as e:
        print("Can't log into Ftrack with used credentials:")
        ftrack_cred = {
            "Ftrack server": str(url),
            "Username": str(user),
            "API key": str(api)
        }
        item_lens = [len(key) + 1 for key in ftrack_cred.keys()]
        justify_len = max(*item_lens)
        for key, value in ftrack_cred.items():
            print("{} {}".format(
                (key + ":").ljust(justify_len, " "),
                value
            ))
        return False

    print('DEBUG: Credentials Username: "{}", API key: "{}" are valid.'.format(
        user, api
    ))
    return True


def legacy_server(ftrack_url):
    # Current file
    scripts_dir = os.path.join(FTRACK_MODULE_DIR, "scripts")

    min_fail_seconds = 5
    max_fail_count = 3
    wait_time_after_max_fail = 10

    subproc = None
    subproc_path = "{}/sub_legacy_server.py".format(scripts_dir)
    subproc_last_failed = datetime.datetime.now()
    subproc_failed_count = 0

    ftrack_accessible = False
    printed_ftrack_error = False

    while True:
        if not ftrack_accessible:
            ftrack_accessible = check_ftrack_url(ftrack_url)

        # Run threads only if Ftrack is accessible
        if not ftrack_accessible and not printed_ftrack_error:
            print("Can't access Ftrack {} <{}>".format(
                ftrack_url, str(datetime.datetime.now())
            ))
            if subproc is not None:
                if subproc.poll() is None:
                    subproc.terminate()

                subproc = None

            printed_ftrack_error = True

            time.sleep(1)
            continue

        printed_ftrack_error = False

        if subproc is None:
            if subproc_failed_count < max_fail_count:
                args = get_openpype_execute_args("run", subproc_path)
                subproc = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE
                )
            elif subproc_failed_count == max_fail_count:
                print((
                    "Storer failed {}times I'll try to run again {}s later"
                ).format(str(max_fail_count), str(wait_time_after_max_fail)))
                subproc_failed_count += 1
            elif ((
                datetime.datetime.now() - subproc_last_failed
            ).seconds > wait_time_after_max_fail):
                subproc_failed_count = 0

        # If thread failed test Ftrack and Mongo connection
        elif subproc.poll() is not None:
            subproc = None
            ftrack_accessible = False

            _subproc_last_failed = datetime.datetime.now()
            delta_time = (_subproc_last_failed - subproc_last_failed).seconds
            if delta_time < min_fail_seconds:
                subproc_failed_count += 1
            else:
                subproc_failed_count = 0
            subproc_last_failed = _subproc_last_failed

        time.sleep(1)


def main_loop(ftrack_url):
    """ This is main loop of event handling.

    Loop is handling threads which handles subprocesses of event storer and
    processor. When one of threads is stopped it is tested to connect to
    ftrack and mongo server. Threads are not started when ftrack or mongo
    server is not accessible. When threads are started it is checked for socket
    signals as heartbeat. Heartbeat must become at least once per 30sec
    otherwise thread will be killed.
    """

    os.environ["FTRACK_EVENT_SUB_ID"] = str(uuid.uuid1())

    mongo_uri = OpenPypeMongoConnection.get_default_mongo_url()

    # Current file
    scripts_dir = os.path.join(FTRACK_MODULE_DIR, "scripts")

    min_fail_seconds = 5
    max_fail_count = 3
    wait_time_after_max_fail = 10

    # Threads data
    storer_name = "StorerThread"
    storer_port = 10001
    storer_path = "{}/sub_event_storer.py".format(scripts_dir)
    storer_thread = None
    storer_last_failed = datetime.datetime.now()
    storer_failed_count = 0

    processor_name = "ProcessorThread"
    processor_port = 10011
    processor_path = "{}/sub_event_processor.py".format(scripts_dir)
    processor_thread = None
    processor_last_failed = datetime.datetime.now()
    processor_failed_count = 0

    statuser_name = "StorerThread"
    statuser_port = 10021
    statuser_path = "{}/sub_event_status.py".format(scripts_dir)
    statuser_thread = None
    statuser_last_failed = datetime.datetime.now()
    statuser_failed_count = 0

    ftrack_accessible = False
    mongo_accessible = False

    printed_ftrack_error = False
    printed_mongo_error = False

    # stop threads on exit
    # TODO check if works and args have thread objects!
    def on_exit(processor_thread, storer_thread, statuser_thread):
        if processor_thread is not None:
            processor_thread.stop()
            processor_thread.join()
            processor_thread = None

        if storer_thread is not None:
            storer_thread.stop()
            storer_thread.join()
            storer_thread = None

        if statuser_thread is not None:
            statuser_thread.stop()
            statuser_thread.join()
            statuser_thread = None

    atexit.register(
        on_exit,
        processor_thread=processor_thread,
        storer_thread=storer_thread,
        statuser_thread=statuser_thread
    )

    host_name = socket.gethostname()
    main_info = [
        ["created_at", datetime.datetime.now().strftime("%Y.%m.%d %H:%M:%S")],
        ["Username", getpass.getuser()],
        ["Host Name", host_name],
        ["Host IP", socket.gethostbyname(host_name)],
        ["OpenPype executable", get_openpype_execute_args()[-1]],
        ["OpenPype version", get_openpype_version() or "N/A"],
        ["OpenPype build version", get_build_version() or "N/A"]
    ]
    main_info_str = json.dumps(main_info)
    # Main loop
    while True:
        # Check if accessible Ftrack and Mongo url
        if not ftrack_accessible:
            ftrack_accessible = check_ftrack_url(ftrack_url)

        if not mongo_accessible:
            mongo_accessible = check_mongo_url(mongo_uri)

        # Run threads only if Ftrack is accessible
        if not ftrack_accessible or not mongo_accessible:
            if not mongo_accessible and not printed_mongo_error:
                print("Can't access Mongo {}".format(mongo_uri))

            if not ftrack_accessible and not printed_ftrack_error:
                print("Can't access Ftrack {}".format(ftrack_url))

            if storer_thread is not None:
                storer_thread.stop()
                storer_thread.join()
                storer_thread = None

            if processor_thread is not None:
                processor_thread.stop()
                processor_thread.join()
                processor_thread = None

            printed_ftrack_error = True
            printed_mongo_error = True

            time.sleep(1)
            continue

        printed_ftrack_error = False
        printed_mongo_error = False

        # ====== STATUSER =======
        if statuser_thread is None:
            if statuser_failed_count < max_fail_count:
                statuser_thread = socket_thread.StatusSocketThread(
                    statuser_name, statuser_port, statuser_path,
                    [main_info_str]
                )
                statuser_thread.start()

            elif statuser_failed_count == max_fail_count:
                print((
                    "Statuser failed {}times in row"
                    " I'll try to run again {}s later"
                ).format(str(max_fail_count), str(wait_time_after_max_fail)))
                statuser_failed_count += 1

            elif ((
                datetime.datetime.now() - statuser_last_failed
            ).seconds > wait_time_after_max_fail):
                statuser_failed_count = 0

        # If thread failed test Ftrack and Mongo connection
        elif not statuser_thread.isAlive():
            statuser_thread.join()
            statuser_thread = None
            ftrack_accessible = False
            mongo_accessible = False

            _processor_last_failed = datetime.datetime.now()
            delta_time = (
                _processor_last_failed - statuser_last_failed
            ).seconds

            if delta_time < min_fail_seconds:
                statuser_failed_count += 1
            else:
                statuser_failed_count = 0
            statuser_last_failed = _processor_last_failed

        elif statuser_thread.stop_subprocess:
            print("Main process was stopped by action")
            on_exit(processor_thread, storer_thread, statuser_thread)
            os.kill(os.getpid(), signal.SIGTERM)
            return 1

        # ====== STORER =======
        # Run backup thread which does not requeire mongo to work
        if storer_thread is None:
            if storer_failed_count < max_fail_count:
                storer_thread = socket_thread.SocketThread(
                    storer_name, storer_port, storer_path
                )
                storer_thread.start()

            elif storer_failed_count == max_fail_count:
                print((
                    "Storer failed {}times I'll try to run again {}s later"
                ).format(str(max_fail_count), str(wait_time_after_max_fail)))
                storer_failed_count += 1
            elif ((
                datetime.datetime.now() - storer_last_failed
            ).seconds > wait_time_after_max_fail):
                storer_failed_count = 0

        # If thread failed test Ftrack and Mongo connection
        elif not storer_thread.isAlive():
            if storer_thread.mongo_error:
                raise MongoPermissionsError()
            storer_thread.join()
            storer_thread = None
            ftrack_accessible = False
            mongo_accessible = False

            _storer_last_failed = datetime.datetime.now()
            delta_time = (_storer_last_failed - storer_last_failed).seconds
            if delta_time < min_fail_seconds:
                storer_failed_count += 1
            else:
                storer_failed_count = 0
            storer_last_failed = _storer_last_failed

        # ====== PROCESSOR =======
        if processor_thread is None:
            if processor_failed_count < max_fail_count:
                processor_thread = socket_thread.SocketThread(
                    processor_name, processor_port, processor_path
                )
                processor_thread.start()

            elif processor_failed_count == max_fail_count:
                print((
                    "Processor failed {}times in row"
                    " I'll try to run again {}s later"
                ).format(str(max_fail_count), str(wait_time_after_max_fail)))
                processor_failed_count += 1

            elif ((
                datetime.datetime.now() - processor_last_failed
            ).seconds > wait_time_after_max_fail):
                processor_failed_count = 0

        # If thread failed test Ftrack and Mongo connection
        elif not processor_thread.isAlive():
            if processor_thread.mongo_error:
                raise Exception(
                    "Exiting because have issue with acces to MongoDB"
                )
            processor_thread.join()
            processor_thread = None
            ftrack_accessible = False
            mongo_accessible = False

            _processor_last_failed = datetime.datetime.now()
            delta_time = (
                _processor_last_failed - processor_last_failed
            ).seconds

            if delta_time < min_fail_seconds:
                processor_failed_count += 1
            else:
                processor_failed_count = 0
            processor_last_failed = _processor_last_failed

        if statuser_thread is not None:
            statuser_thread.set_process("storer", storer_thread)
            statuser_thread.set_process("processor", processor_thread)

        time.sleep(1)


def run_event_server(
    ftrack_url,
    ftrack_user,
    ftrack_api_key,
    legacy,
    clockify_api_key,
    clockify_workspace
):
    if not ftrack_user or not ftrack_api_key:
        print((
            "Ftrack user/api key were not passed."
            " Trying to use credentials from user keyring."
        ))
        cred = credentials.get_credentials(ftrack_url)
        ftrack_user = cred.get("username")
        ftrack_api_key = cred.get("api_key")

    if clockify_workspace and clockify_api_key:
        os.environ["CLOCKIFY_WORKSPACE"] = clockify_workspace
        os.environ["CLOCKIFY_API_KEY"] = clockify_api_key

    # Check url regex and accessibility
    ftrack_url = check_ftrack_url(ftrack_url)
    if not ftrack_url:
        print('Exiting! < Please enter Ftrack server url >')
        return 1

    # Validate entered credentials
    if not validate_credentials(ftrack_url, ftrack_user, ftrack_api_key):
        print('Exiting! < Please enter valid credentials >')
        return 1

    # Set Ftrack environments
    os.environ["FTRACK_SERVER"] = ftrack_url
    os.environ["FTRACK_API_USER"] = ftrack_user
    os.environ["FTRACK_API_KEY"] = ftrack_api_key

    if legacy:
        return legacy_server(ftrack_url)

    return main_loop(ftrack_url)
