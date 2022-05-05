# -*- coding: utf-8 -*-
"""Utility functions used for Avalon - Harmony integration."""
import subprocess
import threading
import os
import random
import zipfile
import sys
import filecmp
import shutil
import logging
import contextlib
import json
import signal
import time
from uuid import uuid4
from Qt import QtWidgets, QtCore, QtGui
import collections

from .server import Server

from openpype.tools.stdout_broker.app import StdOutBroker
from openpype.tools.utils import host_tools
from openpype import style
from openpype.lib.applications import get_non_python_host_kwargs

# Setup logging.
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class ProcessContext:
    server = None
    pid = None
    process = None
    application_path = None
    callback_queue = collections.deque()
    workfile_path = None
    port = None
    stdout_broker = None
    workfile_tool = None

    @classmethod
    def execute_in_main_thread(cls, func_to_call_from_main_thread):
        cls.callback_queue.append(func_to_call_from_main_thread)

    @classmethod
    def main_thread_listen(cls):
        if cls.callback_queue:
            callback = cls.callback_queue.popleft()
            callback()
        if cls.process is not None and cls.process.poll() is not None:
            log.info("Server is not running, closing")
            ProcessContext.stdout_broker.stop()
            QtWidgets.QApplication.quit()


def signature(postfix="func") -> str:
    """Return random ECMA6 compatible function name.

    Args:
        postfix (str): name to append to random string.
    Returns:
        str: random function name.

    """
    return "f{}_{}".format(str(uuid4()).replace("-", "_"), postfix)


class _ZipFile(zipfile.ZipFile):
    """Extended check for windows invalid characters."""

    # this is extending default zipfile table for few invalid characters
    # that can come from Mac
    _windows_illegal_characters = ":<>|\"?*\r\n\x00"
    _windows_illegal_name_trans_table = str.maketrans(
        _windows_illegal_characters,
        "_" * len(_windows_illegal_characters)
    )


def main(*subprocess_args):
    # coloring in StdOutBroker
    os.environ["OPENPYPE_LOG_NO_COLORS"] = "False"
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    icon = QtGui.QIcon(style.get_app_icon_path())
    app.setWindowIcon(icon)

    ProcessContext.stdout_broker = StdOutBroker('harmony')
    ProcessContext.stdout_broker.start()
    launch(*subprocess_args)

    loop_timer = QtCore.QTimer()
    loop_timer.setInterval(20)

    loop_timer.timeout.connect(ProcessContext.main_thread_listen)
    loop_timer.start()

    sys.exit(app.exec_())


def setup_startup_scripts():
    """Manages installation of avalon's TB_sceneOpened.js for Harmony launch.

    If a studio already has defined "TOONBOOM_GLOBAL_SCRIPT_LOCATION", copies
    the TB_sceneOpened.js to that location if the file is different.
    Otherwise, will set the env var to point to the avalon/harmony folder.

    Admins should be aware that this will overwrite TB_sceneOpened in the
    "TOONBOOM_GLOBAL_SCRIPT_LOCATION", and that if they want to have additional
    logic, they will need to one of the following:
        * Create a Harmony package to manage startup logic
        * Use TB_sceneOpenedUI.js instead to manage startup logic
        * Add their startup logic to avalon/harmony/TB_sceneOpened.js
    """
    avalon_dcc_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                  "api")
    startup_js = "TB_sceneOpened.js"

    if os.getenv("TOONBOOM_GLOBAL_SCRIPT_LOCATION"):

        avalon_harmony_startup = os.path.join(avalon_dcc_dir, startup_js)

        env_harmony_startup = os.path.join(
            os.getenv("TOONBOOM_GLOBAL_SCRIPT_LOCATION"), startup_js)

        if not filecmp.cmp(avalon_harmony_startup, env_harmony_startup):
            try:
                shutil.copy(avalon_harmony_startup, env_harmony_startup)
            except Exception as e:
                log.error(e)
                log.warning(
                    "Failed to copy {0} to {1}! "
                    "Defaulting to Avalon TOONBOOM_GLOBAL_SCRIPT_LOCATION."
                    .format(avalon_harmony_startup, env_harmony_startup))

                os.environ["TOONBOOM_GLOBAL_SCRIPT_LOCATION"] = avalon_dcc_dir
    else:
        os.environ["TOONBOOM_GLOBAL_SCRIPT_LOCATION"] = avalon_dcc_dir


def check_libs():
    """Check if `OpenHarmony`_ is available.

    Avalon expects either path in `LIB_OPENHARMONY_PATH` or `openHarmony.js`
    present in `TOONBOOM_GLOBAL_SCRIPT_LOCATION`.

    Throws:
        RuntimeError: If openHarmony is not found.

    .. _OpenHarmony:
        https://github.com/cfourney/OpenHarmony

    """
    if not os.getenv("LIB_OPENHARMONY_PATH"):

        if os.getenv("TOONBOOM_GLOBAL_SCRIPT_LOCATION"):
            if os.path.exists(
                os.path.join(
                    os.getenv("TOONBOOM_GLOBAL_SCRIPT_LOCATION"),
                    "openHarmony.js")):

                os.environ["LIB_OPENHARMONY_PATH"] = \
                    os.getenv("TOONBOOM_GLOBAL_SCRIPT_LOCATION")
                return

        else:
            log.error(("Cannot find OpenHarmony library. "
                       "Please set path to it in LIB_OPENHARMONY_PATH "
                       "environment variable."))
            raise RuntimeError("Missing OpenHarmony library.")


def launch(application_path, *args):
    """Set Harmony for launch.

    Launches Harmony and the server, then starts listening on the main thread
    for callbacks from the server. This is to have Qt applications run in the
    main thread.

    Args:
        application_path (str): Path to Harmony.

    """
    from openpype.pipeline import install_host
    from openpype.hosts.harmony import api as harmony

    install_host(harmony)

    ProcessContext.port = random.randrange(49152, 65535)
    os.environ["AVALON_HARMONY_PORT"] = str(ProcessContext.port)
    ProcessContext.application_path = application_path

    # Launch Harmony.
    setup_startup_scripts()
    check_libs()

    if not os.environ.get("AVALON_HARMONY_WORKFILES_ON_LAUNCH", False):
        open_empty_workfile()
        return

    ProcessContext.workfile_tool = host_tools.get_tool_by_name("workfiles")
    host_tools.show_workfiles(save=False)
    ProcessContext.execute_in_main_thread(check_workfiles_tool)


def check_workfiles_tool():
    if ProcessContext.workfile_tool.isVisible():
        ProcessContext.execute_in_main_thread(check_workfiles_tool)
    elif not ProcessContext.workfile_path:
        open_empty_workfile()


def open_empty_workfile():
    zip_file = os.path.join(os.path.dirname(__file__), "temp.zip")
    temp_path = get_local_harmony_path(zip_file)
    if os.path.exists(temp_path):
        log.info(f"removing existing {temp_path}")
        try:
            shutil.rmtree(temp_path)
        except Exception as e:
            log.critical(f"cannot clear {temp_path}")
            raise Exception(f"cannot clear {temp_path}") from e

    launch_zip_file(zip_file)


def get_local_harmony_path(filepath):
    """From the provided path get the equivalent local Harmony path."""
    basename = os.path.splitext(os.path.basename(filepath))[0]
    harmony_path = os.path.join(os.path.expanduser("~"), ".avalon", "harmony")
    return os.path.join(harmony_path, basename)


def launch_zip_file(filepath):
    """Launch a Harmony application instance with the provided zip file.

    Args:
        filepath (str): Path to file.
    """
    print(f"Localizing {filepath}")

    temp_path = get_local_harmony_path(filepath)
    scene_path = os.path.join(
        temp_path, os.path.basename(temp_path) + ".xstage"
    )
    unzip = False
    if os.path.exists(scene_path):
        # Check remote scene is newer than local.
        if os.path.getmtime(scene_path) < os.path.getmtime(filepath):
            try:
                shutil.rmtree(temp_path)
            except Exception as e:
                log.error(e)
                raise Exception("Cannot delete working folder") from e
            unzip = True
    else:
        unzip = True

    if unzip:
        with _ZipFile(filepath, "r") as zip_ref:
            zip_ref.extractall(temp_path)

    # Close existing scene.
    if ProcessContext.pid:
        os.kill(ProcessContext.pid, signal.SIGTERM)

    # Stop server.
    if ProcessContext.server:
        ProcessContext.server.stop()

    # Launch Avalon server.
    ProcessContext.server = Server(ProcessContext.port)
    ProcessContext.server.start()
    # thread = threading.Thread(target=self.server.start)
    # thread.daemon = True
    # thread.start()

    # Save workfile path for later.
    ProcessContext.workfile_path = filepath

    # find any xstage files is directory, prefer the one with the same name
    # as directory (plus extension)
    xstage_files = []
    for _, _, files in os.walk(temp_path):
        for file in files:
            if os.path.splitext(file)[1] == ".xstage":
                xstage_files.append(file)

    if not os.path.basename("temp.zip"):
        if not xstage_files:
            ProcessContext.server.stop()
            print("no xstage file was found")
            return

    # try to use first available
    scene_path = os.path.join(
        temp_path, xstage_files[0]
    )

    # prefer the one named as zip file
    zip_based_name = "{}.xstage".format(
        os.path.splitext(os.path.basename(filepath))[0])

    if zip_based_name in xstage_files:
        scene_path = os.path.join(
            temp_path, zip_based_name
        )

    if not os.path.exists(scene_path):
        print("error: cannot determine scene file")
        ProcessContext.server.stop()
        return

    print("Launching {}".format(scene_path))
    kwargs = get_non_python_host_kwargs({}, False)
    process = subprocess.Popen(
        [ProcessContext.application_path, scene_path],
        **kwargs
    )
    ProcessContext.pid = process.pid
    ProcessContext.process = process
    ProcessContext.stdout_broker.host_connected()


def on_file_changed(path, threaded=True):
    """Threaded zipping and move of the project directory.

    This method is called when the `.xstage` file is changed.
    """
    log.debug("File changed: " + path)

    if ProcessContext.workfile_path is None:
        return

    if threaded:
        thread = threading.Thread(
            target=zip_and_move,
            args=(os.path.dirname(path), ProcessContext.workfile_path)
        )
        thread.start()
    else:
        zip_and_move(os.path.dirname(path), ProcessContext.workfile_path)


def zip_and_move(source, destination):
    """Zip a directory and move to `destination`.

    Args:
        source (str): Directory to zip and move to destination.
        destination (str): Destination file path to zip file.

    """
    os.chdir(os.path.dirname(source))
    shutil.make_archive(os.path.basename(source), "zip", source)
    with _ZipFile(os.path.basename(source) + ".zip") as zr:
        if zr.testzip() is not None:
            raise Exception("File archive is corrupted.")
    shutil.move(os.path.basename(source) + ".zip", destination)
    log.debug(f"Saved '{source}' to '{destination}'")


def show(tool_name):
    """Call show on "module_name".

    This allows to make a QApplication ahead of time and always "exec_" to
    prevent crashing.

    Args:
        module_name (str): Name of module to call "show" on.

    """
    # Requests often get doubled up when showing tools, so we wait a second for
    # requests to be received properly.
    time.sleep(1)

    kwargs = {}
    if tool_name == "loader":
        kwargs["use_context"] = True

    ProcessContext.execute_in_main_thread(
        lambda: host_tools.show_tool_by_name(tool_name, **kwargs)
    )

    # Required return statement.
    return "nothing"


def get_scene_data():
    try:
        return send(
            {
                "function": "AvalonHarmony.getSceneData"
            })["result"]
    except json.decoder.JSONDecodeError:
        # Means no sceen metadata has been made before.
        return {}
    except KeyError:
        # Means no existing scene metadata has been made.
        return {}


def set_scene_data(data):
    """Write scene data to metadata.

    Args:
        data (dict): Data to write.

    """
    # Write scene data.
    send(
        {
            "function": "AvalonHarmony.setSceneData",
            "args": data
        })


def read(node_id):
    """Read object metadata in to a dictionary.

    Args:
        node_id (str): Path to node or id of object.

    Returns:
        dict
    """
    scene_data = get_scene_data()
    if node_id in scene_data:
        return scene_data[node_id]

    return {}


def remove(node_id):
    """
        Remove node data from scene metadata.

        Args:
            node_id (str): full name (eg. 'Top/renderAnimation')
    """
    data = get_scene_data()
    del data[node_id]
    set_scene_data(data)


def delete_node(node):
    """ Physically delete node from scene. """
    send(
        {
            "function": "AvalonHarmony.deleteNode",
            "args": node
        }
    )


def imprint(node_id, data, remove=False):
    """Write `data` to the `node` as json.

    Arguments:
        node_id (str): Path to node or id of object.
        data (dict): Dictionary of key/value pairs.
        remove (bool): Removes the data from the scene.

    Example:
        >>> from openpype.hosts.harmony.api import lib
        >>> node = "Top/Display"
        >>> data = {"str": "someting", "int": 1, "float": 0.32, "bool": True}
        >>> lib.imprint(layer, data)
    """
    scene_data = get_scene_data()

    if remove and (node_id in scene_data):
        scene_data.pop(node_id, None)
    else:
        if node_id in scene_data:
            scene_data[node_id].update(data)
        else:
            scene_data[node_id] = data

    set_scene_data(scene_data)


@contextlib.contextmanager
def maintained_selection():
    """Maintain selection during context."""

    selected_nodes = send(
        {
            "function": "AvalonHarmony.getSelectedNodes"
        })["result"]

    try:
        yield selected_nodes
    finally:
        selected_nodes = send(
            {
                "function": "AvalonHarmony.selectNodes",
                "args": selected_nodes
            }
        )


def send(request):
    """Public method for sending requests to Harmony."""
    return ProcessContext.server.send(request)


def select_nodes(nodes):
    """ Selects nodes in Node View """
    _ = send(
        {
            "function": "AvalonHarmony.selectNodes",
            "args": nodes
        }
    )


@contextlib.contextmanager
def maintained_nodes_state(nodes):
    """Maintain nodes states during context."""
    # Collect current state.
    states = send(
        {
            "function": "AvalonHarmony.areEnabled", "args": nodes
        })["result"]

    # Disable all nodes.
    send(
        {
            "function": "AvalonHarmony.disableNodes", "args": nodes
        })

    try:
        yield
    finally:
        send(
            {
                "function": "AvalonHarmony.setState",
                "args": [nodes, states]
            })


def save_scene():
    """Save the Harmony scene safely.

    The built-in (to Avalon) background zip and moving of the Harmony scene
    folder, interfers with server/client communication by sending two requests
    at the same time. This only happens when sending "scene.saveAll()". This
    method prevents this double request and safely saves the scene.

    """
    # Need to turn off the backgound watcher else the communication with
    # the server gets spammed with two requests at the same time.
    scene_path = send(
        {"function": "AvalonHarmony.saveScene"})["result"]

    # Manually update the remote file.
    on_file_changed(scene_path, threaded=False)

    # Re-enable the background watcher.
    send({"function": "AvalonHarmony.enableFileWather"})


def save_scene_as(filepath):
    """Save Harmony scene as `filepath`."""
    scene_dir = os.path.dirname(filepath)
    destination = os.path.join(
        os.path.dirname(ProcessContext.workfile_path),
        os.path.splitext(os.path.basename(filepath))[0] + ".zip"
    )

    if os.path.exists(scene_dir):
        try:
            shutil.rmtree(scene_dir)
        except Exception as e:
            log.error(f"Cannot remove {scene_dir}")
            raise Exception(f"Cannot remove {scene_dir}") from e

    send(
        {"function": "scene.saveAs", "args": [scene_dir]}
    )["result"]

    zip_and_move(scene_dir, destination)

    ProcessContext.workfile_path = destination

    send(
        {"function": "AvalonHarmony.addPathToWatcher", "args": filepath}
    )


def find_node_by_name(name, node_type):
    """Find node by its name.

    Args:
        name (str): Name of the Node. (without part before '/')
        node_type (str): Type of the Node.
            'READ' - for loaded data with Loaders (background)
            'GROUP' - for loaded data with Loaders (templates)
            'WRITE' - render nodes

    Returns:
        str: FQ Node name.

    """
    nodes = send(
        {"function": "node.getNodes", "args": [[node_type]]}
    )["result"]
    for node in nodes:
        node_name = node.split("/")[-1]
        if name == node_name:
            return node

    return None
