import sys
from pype.ftrack import credentials
from pype.ftrack.ftrack_server import FtrackServer
from pypeapp import api

log = api.Logger().get_logger(__name__, "ftrack-event-server-cli")

possible_yes = ['y', 'yes']
possible_no = ['n', 'no']
possible_third = ['a', 'auto']
possible_exit = ['exit']


def ask_yes_no(third=False):
    msg = "Y/N:"
    if third:
        msg = "Y/N/AUTO:"
    log.info(msg)
    response = input().lower()
    if response in possible_exit:
        sys.exit()
    elif response in possible_yes:
        return True
    elif response in possible_no:
        return False
    else:
        all_entries = possible_no
        all_entries.extend(possible_yes)
        if third is True:
            if response in possible_third:
                return 'auto'
            else:
                all_entries.extend(possible_third)
        all_entries.extend(possible_exit)
        all_entries = ', '.join(all_entries)
        log.info(
            'Invalid input. Possible entries: [{}]. Try it again:'.foramt(
                all_entries
            )
        )
        return ask_yes_no()


def cli_login():
    enter_cred = True
    cred_data = credentials._get_credentials(True)

    user = cred_data.get('username', None)
    key = cred_data.get('apiKey', None)
    auto = cred_data.get('auto_connect', False)
    if user is None or key is None:
        log.info(
            'Credentials are not set. Do you want to enter them now? (Y/N)'
        )
        if ask_yes_no() is False:
            log.info("Exiting...")
            return
    elif credentials._check_credentials(user, key):
        if auto is False:
            log.info((
                'Do you want to log with username {}'
                ' enter "auto" if want to autoconnect next time (Y/N/AUTO)'
            ).format(
                user
            ))
            result = ask_yes_no(True)
            if result is True:
                enter_cred = False
            elif result == 'auto':
                credentials._save_credentials(user, key, True, True)
                enter_cred = False
        else:
            enter_cred = False
    else:
        log.info(
            'Stored credentials are not valid.'
            ' Do you want enter them now?(Y/N)'
        )
        if ask_yes_no() is False:
            log.info("Exiting...")
            return

    while enter_cred:
        log.info('Please enter Ftrack API User:')
        user = input()
        log.info('And now enter Ftrack API Key:')
        key = input()
        if credentials._check_credentials(user, key):
            log.info(
                'Credentials are valid.'
                ' Do you want to auto-connect next time?(Y/N)'
            )
            credentials._save_credentials(user, key, True, ask_yes_no())
            enter_cred = False
            break
        else:
            log.info(
                'Entered credentials are not valid.'
                ' Do you want to try it again?(Y/N)'
            )
            if ask_yes_no() is False:
                log.info('Exiting...')
                return

    server = FtrackServer('event')
    server.run_server()


def main():
    cli_login()


if (__name__ == ('__main__')):
    main()
