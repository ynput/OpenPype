import os
import json
import platform

import appdirs


def _get_servers_path():
    dirpath = appdirs.user_data_dir("openpype", "pypeclub")
    return os.path.join(dirpath, "used_servers.json")


def get_servers_info_data():
    data = {}
    servers_info_path = _get_servers_path()
    if not os.path.exists(servers_info_path):
        dirpath = os.path.dirname(servers_info_path)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

        with open(servers_info_path, "w") as stream:
            json.dump(data, stream)
        return data

    with open(servers_info_path, "r") as stream:
        try:
            data = json.load(stream)
        except BaseException:
            pass
    return data


def get_last_server():
    data = get_servers_info_data()
    return data.get("last_server")


def add_server(url):
    servers_info_path = _get_servers_path()
    data = get_servers_info_data()
    data["last_server"] = url
    with open(servers_info_path, "w") as stream:
        json.dump(data, stream)


class TokenKeyring:
    # Fake username with hardcoded username
    username_key = "username"

    def __init__(self, url):
        try:
            import keyring

        except Exception:
            raise NotImplementedError(
                "Python module `keyring` is not available."
            )

        # hack for cx_freeze and Windows keyring backend
        if platform.system().lower() == "windows":
            from keyring.backends import Windows

            keyring.set_keyring(Windows.WinVaultKeyring())

        self._url = url
        self._keyring_key = "OpenPype/{}".format(url)

    def get_value(self):
        import keyring

        return keyring.get_password(self._keyring_key, self.username_key)

    def set_value(self, value):
        import keyring

        keyring.set_password(self._keyring_key, self.username_key, value)


def load_token(url):
    return TokenKeyring(url).get_value()


def store_token(url, token):
    TokenKeyring(url).set_value(token)


def ask_to_login_ui(*args, **kwargs):
    from .ui import ask_to_login

    return ask_to_login(*args, **kwargs)
