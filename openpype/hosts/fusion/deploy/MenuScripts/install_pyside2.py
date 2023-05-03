# This is just a quick hack for users running Py3 locally but having no
# Qt library installed
import os
import subprocess
import importlib


def get_python_path():
    fusion_py_envs = [
        "FUSION_PYTHON36_HOME",
        "FUSION16_PYTHON36_HOME",
        "FUSION_PYTHON3_HOME",
    ]

    for env in fusion_py_envs:
        if os.environ.get(env) is not None:
            return os.environ.get(env)


try:
    from qtpy import API_NAME

    print(f"Qt binding: {API_NAME}")
    mod = importlib.import_module(API_NAME)
    print(f"Qt path: {mod.__file__}")
    print("Qt library found, nothing to do..")

except:
    python_path = get_python_path()
    if python_path == None:
        print("Can't find any any python environment.")

    print("Assuming no Qt library is installed..")
    print(f"Installing PySide2 for Python 3.6: {python_path}")

    # Get full path to python executable
    exe = "python.exe" if os.name == "nt" else "python"
    python = os.path.join(python_path, exe)
    assert os.path.exists(python), f"Python doesn't exist: {python}"

    # Do python -m pip install PySide2
    args = [python, "-m", "pip", "install", "PySide2"]
    print(f"Args: {args}")
    subprocess.Popen(args)
