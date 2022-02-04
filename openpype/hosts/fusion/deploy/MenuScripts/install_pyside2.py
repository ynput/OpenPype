# This is just a quick hack for users running Py3 locally but having no
# Qt library installed
import os

try:
    print("Qt library found, nothing to do.")
    from Qt import QtWidgets
except ImportError as exc:
    print("Assuming no Qt library is installed..")
    print('Installing PySide2 for Python 3.6: '
          f'{os.environ["FUSION16_PYTHON36_HOME"]}')

    import subprocess
    subprocess.Popen(["pip", "install", "PySide2"])
