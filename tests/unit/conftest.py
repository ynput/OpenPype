import os

os.environ["OPENPYPE_DATABASE_NAME"] = "openpype"

import openpype

openpype_root = os.path.dirname(os.path.dirname(openpype.__file__))

# ?? why 2 of those
os.environ["OPENPYPE_ROOT"] = openpype_root
os.environ["OPENPYPE_REPOS_ROOT"] = openpype_root
