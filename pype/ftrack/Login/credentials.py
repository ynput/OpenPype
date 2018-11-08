import os
import toml
# import ftrack_api

# TODO JUST TEST PATH - path should be in Environment Variables...
config_path = r"C:\test"
config_name = 'credentials.toml'
fpath = os.path.join(config_path, config_name)

def _get_credentials():
    try:
        file = open(fpath, 'r')
    except:
        file = open(fpath, 'w')

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

def _check_credentials(username, apiKey):

    _set_env(username, apiKey)

    try:
        session = ftrack_api.Session()
        return True
    except Exception as e:
        print(e)
        return False
