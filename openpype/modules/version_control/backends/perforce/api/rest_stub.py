import six
import os
import requests

from openpype.modules.version_control.backends import abstract

if six.PY2:
    import pathlib2 as pathlib
else:
    import pathlib

_typing = False
if _typing:
    from typing import Any
    from typing import Sequence
del _typing


class PerforceRestStub(abstract.VersionControl):

    @staticmethod
    def _wrap_call(command, **kwargs):
        webserver_url = os.environ.get("PERFORCE_WEBSERVER_URL")
        if not webserver_url:
            raise RuntimeError("Uknown url for Perforce")

        action_url = f"{webserver_url}/perforce/{command}"

        response = requests.post(
            action_url, json=kwargs
        )
        if not response.ok:
            print(response.content)
            raise RuntimeError(response.text)
        return response.json()


    @staticmethod
    def add(path, comment=""):
        # type: (pathlib.Path | str, str) -> bool
        response = PerforceRestStub._wrap_call("add",
                                               path=path,
                                               comment=comment)
        return response

    @staticmethod
    def checkout(path, comment=""):
        response = PerforceRestStub._wrap_call("checkout",
                                               path=path,
                                               comment=comment)
        return response


    @staticmethod
    def submit_change_list(comment):
        response = PerforceRestStub._wrap_call("submit_change_list",
                                               comment=comment)
        return response
