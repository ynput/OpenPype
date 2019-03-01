import os
import json
import appdirs
import ftrack_api
from . import FtrackServer
from app import api

log = api.Logger.getLogger(__name__, "ftrack-event-server-cli")


def check_cred(user, key):
    os.environ["FTRACK_API_USER"] = user
    os.environ["FTRACK_API_KEY"] = key

    try:
        session = ftrack_api.Session()
        session.close()
        return True
    except Exception:
        return False


def ask_yes_no():
    possible_yes = ["y", "yes"]
    possible_no = ["n", "no"]
    log.info("Y/N:")
    cont = input()
    if cont.lower() in possible_yes:
        return True
    elif cont.lower() in possible_no:
        return False
    else:
        log.info(
            "Invalid input. Possible entries: [y, yes, n, no]. Try it again:"
        )
        return ask_yes_no()


def cli_login():
    config_path = os.path.normpath(appdirs.user_data_dir('pype-app', 'pype'))
    config_name = 'ftrack_event_cred.json'
    event_credentials_file = os.path.join(config_path, config_name)

    if not os.path.isdir(config_path):
        os.makedirs(config_path)
    if not os.path.exists(event_credentials_file):
        open(event_credentials_file, 'w').close()
    enter_cred = True

    with open(event_credentials_file, 'r') as fp:
        try:
            cred_data = json.load(fp)
        except Exception:
            cred_data = {}

    user = cred_data.get("FTRACK_API_USER", None)
    key = cred_data.get("FTRACK_API_KEY", None)
    auto = cred_data.get("AUTO_CONNECT", False)
    if user is None or key is None:
        log.info("Credentials are not set. Do you want to enter them now? (Y/N)")
        if ask_yes_no() is False:
            log.info("Exiting...")
            return
    elif check_cred(user, key):
        if auto is False:
            log.info("Do you want to log with username {}? (Y/N)".format(
                cred_data["FTRACK_API_USER"]
            ))
            if ask_yes_no():
                enter_cred = False
        else:
            enter_cred = False
    else:
        log.info(
            "Stored credentials are not valid. "
            "Do you want enter them now?(Y/N)"
        )
        if ask_yes_no() is False:
            log.info("Exiting...")
            return

    while enter_cred:
        log.info("Please enter Ftrack API User:")
        user = input()
        log.info("And now enter Ftrack API Key:")
        key = input()
        if check_cred(user, key):
            export = {
                "FTRACK_API_USER": user,
                "FTRACK_API_KEY": key
            }
            log.info(
                "Credentials are valid."
                " Do you want to auto-connect next time?(Y/N)"
            )
            if ask_yes_no():
                export["AUTO_CONNECT"] = True

            with open(event_credentials_file, 'w') as fp:
                json.dump(export, fp)
            enter_cred = False
            break
        else:
            log.info(
                "Entered credentials are not valid."
                " Do you want to try it again?(Y/N)"
            )
            if ask_yes_no() is False:
                log.info("Exiting...")
                return

    server = FtrackServer('event')
    server.run_server()


def main():
    cli_login()


if (__name__ == ('__main__')):
    main()
