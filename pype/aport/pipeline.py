import sys
import os
import getpass

from app.api import Logger
from io_nonsingleton import DbConnector


io = DbConnector()
log = Logger.getLogger(__name__, "aport")

self = sys.modules[__name__]
self.SESSION = None
self._registered_root = {"_": ""}
self.AVALON_PROJECT = os.getenv("AVALON_PROJECT", None)
self.AVALON_ASSET = os.getenv("AVALON_ASSET", None)
self.AVALON_TASK = os.getenv("AVALON_TASK", None)
self.AVALON_SILO = os.getenv("AVALON_SILO", None)


def get_session():
    if not self.SESSION:
        io.install()
        self.SESSION = io.Session

        # for k, v in os.environ.items():
        #     if 'AVALON' in k:
        #         print(str((k, v)))

    return self.SESSION


def update_current_task(task=None, asset=None, app=None):
    """Update active Session to a new task work area.

    This updates the live Session to a different `asset`, `task` or `app`.

    Args:
        task (str): The task to set.
        asset (str): The asset to set.
        app (str): The app to set.

    Returns:
        dict: The changed key, values in the current Session.

    """

    mapping = {
        "AVALON_ASSET": asset,
        "AVALON_TASK": task,
        "AVALON_APP": app,
    }
    changed = {key: value for key, value in mapping.items() if value}
    if not changed:
        return

    # Update silo when asset changed
    if "AVALON_ASSET" in changed:
        asset_document = io.find_one({"name": changed["AVALON_ASSET"],
                                      "type": "asset"})
        assert asset_document, "Asset must exist"
        silo = asset_document["silo"]
        if silo is None:
            silo = asset_document["name"]
        changed["AVALON_SILO"] = silo
        parents = asset_document['data']['parents']
        hierarchy = ""
        if len(parents) > 0:
            hierarchy = os.path.sep.join(parents)
        changed['AVALON_HIERARCHY'] = hierarchy

    # Compute work directory (with the temporary changed session so far)
    project = io.find_one({"type": "project"},
                          projection={"config.template.work": True})
    template = project["config"]["template"]["work"]
    _session = self.SESSION.copy()
    _session.update(changed)
    changed["AVALON_WORKDIR"] = _format_work_template(template, _session)

    # Update the full session in one go to avoid half updates
    self.SESSION.update(changed)

    # Update the environment
    os.environ.update(changed)

    return changed


def _format_work_template(template, session=None):
    """Return a formatted configuration template with a Session.

    Note: This *cannot* format the templates for published files since the
        session does not hold the context for a published file. Instead use
        `get_representation_path` to parse the full path to a published file.

    Args:
        template (str): The template to format.
        session (dict, Optional): The Session to use. If not provided use the
            currently active global Session.

    Returns:
        str: The fully formatted path.

    """
    if session is None:
        session = self.SESSION

    project = io.find_one({'type': 'project'})

    return template.format(**{
        "root": registered_root(),
        "project": {
            "name": project.get("name", session["AVALON_PROJECT"]),
            "code": project["data"].get("code", ''),
        },
        "silo": session["AVALON_SILO"],
        "hierarchy": session['AVALON_HIERARCHY'],
        "asset": session["AVALON_ASSET"],
        "task": session["AVALON_TASK"],
        "app": session["AVALON_APP"],
        "user": session.get("AVALON_USER", getpass.getuser())
    })


def registered_root():
    """Return currently registered root"""
    return os.path.normpath(
        self._registered_root["_"]
        or self.SESSION.get("AVALON_PROJECTS") or ""
    )
