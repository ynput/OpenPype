import os
import json
from pype.vendor import ftrack_api
import appdirs


config_path = os.path.normpath(appdirs.user_data_dir('pype-app', 'pype'))
action_file_name = 'ftrack_cred.json'
event_file_name = 'ftrack_event_cred.json'
action_fpath = os.path.join(config_path, action_file_name)
event_fpath = os.path.join(config_path, event_file_name)
folders = set([os.path.dirname(action_fpath), os.path.dirname(event_fpath)])

for folder in folders:
    if not os.path.isdir(folder):
        os.makedirs(folder)


def _get_credentials(event=False):
    if event:
        fpath = event_fpath
    else:
        fpath = action_fpath

    credentials = {}
    try:
        file = open(fpath, 'r')
        credentials = json.load(file)
    except Exception:
        file = open(fpath, 'w')

    file.close()

    return credentials


def _save_credentials(username, apiKey, event=False, auto_connect=None):
    data = {
        'username': username,
        'apiKey': apiKey
    }

    if event:
        fpath = event_fpath
        if auto_connect is None:
            cred = _get_credentials(True)
            auto_connect = cred.get('auto_connect', False)
        data['auto_connect'] = auto_connect
    else:
        fpath = action_fpath

    file = open(fpath, 'w')
    file.write(json.dumps(data))
    file.close()


def _clear_credentials(event=False):
    if event:
        fpath = event_fpath
    else:
        fpath = action_fpath
    open(fpath, 'w').close()
    _set_env(None, None)


def _set_env(username, apiKey):
    if not username:
        username = ''
    if not apiKey:
        apiKey = ''
    os.environ['FTRACK_API_USER'] = username
    os.environ['FTRACK_API_KEY'] = apiKey


def _check_credentials(username=None, apiKey=None):

    if username and apiKey:
        _set_env(username, apiKey)

    try:
        session = ftrack_api.Session()
        session.close()
    except Exception as e:
        return False

    return True
