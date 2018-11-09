import os
import toml
import ftrack_api
import appdirs 

config_path = os.path.normpath(appdirs.user_data_dir('pype-app','pype'))
config_name = 'credentials.toml'
fpath = os.path.join(config_path, config_name)

def _get_credentials():

    folder = os.path.dirname(fpath)

    if not os.path.isdir(folder):
        os.makedirs(folder)

    try:
        file = open(fpath, 'r')
    except:
        filecreate = open(fpath, 'w')
        filecreate.close()
        file = open(fpath, 'r')

    credentials = toml.load(file)
    file.close()

    return credentials

def _save_credentials(username, apiKey):
    file = open(fpath, 'w')

    data = {
        'username':username,
        'apiKey':apiKey
    }

    credentials = toml.dumps(data)
    file.write(credentials)
    file.close()

def _clear_credentials():
    file = open(fpath, 'w').close()

def _set_env(username, apiKey):
    os.environ['FTRACK_API_USER'] = username
    os.environ['FTRACK_API_KEY'] = apiKey

def _check_credentials(username=None, apiKey=None):

    if username and apiKey:
        _set_env(username, apiKey)

    try:
        session = ftrack_api.Session()
    except Exception as e:
        print(e)
        return False

    session.close()
    return True
