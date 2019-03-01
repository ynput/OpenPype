import os
import json
import ftrack_api
import appdirs


config_path = os.path.normpath(appdirs.user_data_dir('pype-app', 'pype'))
config_name = 'ftrack_cred.json'
fpath = os.path.join(config_path, config_name)
folder = os.path.dirname(fpath)

if not os.path.isdir(folder):
    os.makedirs(folder)


def _get_credentials():

    folder = os.path.dirname(fpath)

    if not os.path.isdir(folder):
        os.makedirs(folder)

    try:
        file = open(fpath, 'r')
    except Exception:
        filecreate = open(fpath, 'w')
        filecreate.close()
        file = open(fpath, 'r')

    credentials = json.load(file)
    file.close()

    return credentials


def _save_credentials(username, apiKey):
    file = open(fpath, 'w')

    data = {
        'username': username,
        'apiKey': apiKey
    }

    credentials = json.dumps(data)
    file.write(credentials)
    file.close()


def _clear_credentials():
    file = open(fpath, 'w').close()
    _set_env(None, None)


def _set_env(username, apiKey):
    os.environ['FTRACK_API_USER'] = username
    os.environ['FTRACK_API_KEY'] = apiKey


def _check_credentials(username=None, apiKey=None):

    if username and apiKey:
        _set_env(username, apiKey)

    try:
        session = ftrack_api.Session()
        session.close()
    except Exception as e:
        print(e)
        return False

    return True
