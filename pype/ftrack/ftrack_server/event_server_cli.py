import os
import sys
import argparse
import requests
from pype.vendor import ftrack_api
from pype.ftrack import credentials
from pype.ftrack.ftrack_server import FtrackServer
from pypeapp import Logger

log = Logger().get_logger('Ftrack event server', "ftrack-event-server-cli")


def check_url(url):
    if not url:
        log.error('Ftrack URL is not set!')
        return None

    url = url.strip('/ ')

    if 'http' not in url:
        if url.endswith('ftrackapp.com'):
            url = 'https://' + url
        else:
            url = 'https://{0}.ftrackapp.com'.format(url)
    try:
        result = requests.get(url, allow_redirects=False)
    except requests.exceptions.RequestException:
        log.error('Entered Ftrack URL is not accesible!')
        return None

    if (result.status_code != 200 or 'FTRACK_VERSION' not in result.headers):
        log.error('Entered Ftrack URL is not accesible!')
        return None

    log.debug('Ftrack server {} is accessible.'.format(url))

    return url

def validate_credentials(url, user, api):
    first_validation = True
    if not user:
        log.error('Ftrack Username is not set! Exiting.')
        first_validation = False
    if not api:
        log.error('Ftrack API key is not set! Exiting.')
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
        log.error(
            'Can\'t log into Ftrack with used credentials:'
            ' Ftrack server: "{}" // Username: {} // API key: {}'.format(
            url, user, api
        ))
        return False

    log.debug('Credentials Username: "{}", API key: "{}" are valid.'.format(
        user, api
    ))
    return True


def process_event_paths(event_paths):
    log.debug('Processing event paths: {}.'.format(str(event_paths)))
    return_paths = []
    not_found = []
    if not event_paths:
        return return_paths, not_found

    if isinstance(event_paths, str):
        event_paths = event_paths.split(os.pathsep)

    for path in event_paths:
        if os.path.exists(path):
            return_paths.append(path)
        else:
            not_found.append(path)

    return os.pathsep.join(return_paths), not_found


def run_event_server(ftrack_url, username, api_key, event_paths):
    os.environ['FTRACK_SERVER'] = ftrack_url
    os.environ['FTRACK_API_USER'] = username
    os.environ['FTRACK_API_KEY'] = api_key
    os.environ['FTRACK_EVENTS_PATH'] = event_paths

    server = FtrackServer('event')
    server.run_server()

def main(argv):
    '''
    Entered values through args have most priority!
    - all values are overriden with entered values to args

    There is also possibility to set session with only Environments.
    - Required for session: FTRACK_SERVER, FTRACK_API_USER, FTRACK_API_KEY
    - Path to events to load should be set in: FTRACK_EVENTS_PATH
    - "-noloadcred" must be set if want to use environment values!!!

    "-storecred" will store currently set credentials for future use.
    - it's handy to use on first launch

    '''
    parser = argparse.ArgumentParser(description='Ftrack event server')
    parser.add_argument(
        "-ftrackurl", type=str, metavar='FTRACKURL',
        help=(
            "URL to ftrack server where events should handle"
            " (default from environment: $FTRACK_SERVER)"
        )
    )
    parser.add_argument(
        "-ftrackuser", type=str,
        help=(
            "Username should be the username of the user in ftrack"
            " to record operations against."
            " (default from environment: $FTRACK_API_USER)"
        )
    )
    parser.add_argument(
        "-ftrackapikey", type=str,
        help=(
            "Should be the API key to use for authentication"
            " (default from environment: $FTRACK_API_KEY)"
        )
    )
    parser.add_argument(
        "-ftrackeventpaths", nargs='+',
        help=(
            "List of paths where events are stored."
            " (default from environment: $FTRACK_EVENTS_PATH)"
        )
    )
    parser.add_argument(
        '-storecred',
        help=(
            "Entered credentials will be also stored"
            " to apps dir for future usage"
        ),
        action="store_true"
    )
    parser.add_argument(
        '-noloadcred',
        help="Load creadentials from apps dir",
        action="store_true"
    )

    ftrack_url = os.environ.get('FTRACK_SERVER')
    username = os.environ.get('FTRACK_API_USER')
    api_key = os.environ.get('FTRACK_API_KEY')
    event_paths = os.environ.get('FTRACK_EVENTS_PATH')

    kwargs, args = parser.parse_known_args(argv)

    if kwargs.ftrackurl:
        ftrack_url = kwargs.ftrackurl

    if kwargs.ftrackeventpaths:
        event_paths = kwargs.ftrackeventpaths

    if not kwargs.noloadcred:
        cred = credentials._get_credentials(True)
        username = cred.get('username')
        api_key = cred.get('apiKey')

    if kwargs.ftrackuser:
        username = kwargs.ftrackuser

    if kwargs.ftrackapikey:
        api_key = kwargs.ftrackapikey

    # Check url regex and accessibility
    ftrack_url = check_url(ftrack_url)
    if not ftrack_url:
        return 1

    # Validate entered credentials
    if not validate_credentials(ftrack_url, username, api_key):
        return 1

    # Process events path
    event_paths, not_found = process_event_paths(event_paths)
    if not_found:
        log.warning(
            'These paths were not found: {}'.format(str(not_found))
        )
    if not event_paths:
        if not_found:
            log.error('Any of entered paths is valid or can be accesible.')
        else:
            log.error('Paths to events are not set. Exiting.')
        return 1

    if kwargs.storecred:
        credentials._save_credentials(username, api_key, True)

    run_event_server(ftrack_url, username, api_key, event_paths)


if (__name__ == ('__main__')):
    sys.exit(main(sys.argv))
