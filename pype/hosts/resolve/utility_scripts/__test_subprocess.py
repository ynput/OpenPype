#! python3
# -*- coding: utf-8 -*-
import os
from pypeapp import execute, Logger
from pype.hosts.resolve.utils import get_resolve_module

log = Logger().get_logger("Resolve")

CURRENT_DIR = os.getenv("RESOLVE_UTILITY_SCRIPTS_DIR", "")
python_dir = os.getenv("PYTHON36_RESOLVE")
python_exe = os.path.normpath(
    os.path.join(python_dir, "python.exe")
)

resolve = get_resolve_module()
PM = resolve.GetProjectManager()
P = PM.GetCurrentProject()

log.info(P.GetName())


# ______________________________________________________
# testing subprocessing Scripts
testing_py = os.path.join(CURRENT_DIR, "ResolvePageSwitcher.py")
testing_py = os.path.normpath(testing_py)
log.info(f"Testing path to script: `{testing_py}`")

returncode = execute(
    [python_exe, os.path.normpath(testing_py)],
    env=dict(os.environ)
)

# Check if output file exists
if returncode != 0:
    log.error("Executing failed!")
