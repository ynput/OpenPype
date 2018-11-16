import sys
import os
import argparse

from app.lib.utils import forward
from pype.ftrack import credentials, login_dialog as login_dialog

# Validation if alredy logged into Ftrack
def validate():
    validation = False
    cred = credentials._get_credentials()
    if 'username' in cred and 'apiKey' in cred:
        validation = credentials._check_credentials(
            cred['username'],
            cred['apiKey']
        )
        if validation is False:
            login_dialog.run_login()
    else:
        login_dialog.run_login()

    validation = credentials._check_credentials()
    if not validation:
        print("We are unable to connect to Ftrack")
        sys.exit()

# Entered arguments
parser = argparse.ArgumentParser()
parser.add_argument("--actionserver", action="store_true",
                    help="launch action server for ftrack")
parser.add_argument("--eventserver", action="store_true",
                    help="launch action server for ftrack")
parser.add_argument("--logout", action="store_true",
                    help="launch action server for ftrack")
parser.add_argument("--systray", action="store_true",
                    help="launch action server for ftrack")

kwargs, args = parser.parse_known_args()

if kwargs.logout:
    credentials._clear_credentials()
    sys.exit()
else:
    validate()

if kwargs.eventserver:
    fname = os.path.join(os.environ["FTRACK_ACTION_SERVER"], "eventServer.py")
    returncode = forward([
        sys.executable, "-u", fname
    ])

elif kwargs.systray:
    stud_config = os.getenv('PYPE_STUDIO_CONFIG')
    items = [stud_config, "pype", "ftrack", "tray.py"]
    fname = os.path.sep.join(items)

    returncode = forward([
        sys.executable, "-u", fname
    ])

else:
    fname = os.path.join(os.environ["FTRACK_ACTION_SERVER"], "actionServer.py")
    returncode = forward([
        sys.executable, "-u", fname
    ])

sys.exit(returncode)
