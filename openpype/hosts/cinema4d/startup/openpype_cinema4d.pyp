import os
import sys
# C4D doesn't ship with python3.dll which PySide is
# built against. 
# 
# Python3.8+ uses os.add_dll_directory to load dlls
# Previous version just add to the path
if "win" in sys.platform:
    dll_dirs = os.getenv("OPENPYPE_DLL_DIRS") or ""

    for path in dll_dirs.split(os.pathsep):
        if not path:
            continue
        try:
            norm_path = os.path.normpath(path)
            os.add_dll_directory(path)
        except AttributeError:
            os.environ["PATH"] = norm_path + os.pathsep + os.environ["PATH"]

#from openpype.api import get_project_settings
#from openpype.pipeline import install_host
#from openpype.hosts.cinema4d.api import Cinema4DHost





if __name__ == '__main__':
    print("started")
    #host = Cinema4DHost()
    #install_host(host)
