import os
import sys
import hiero
import pyblish.api
import avalon.api as avalon
from avalon.vendor.Qt import (QtWidgets, QtGui)
import pype.api as pype
from pypeapp import Logger


log = Logger().get_logger(__name__, "nukestudio")

cached_process = None


self = sys.modules[__name__]
self._has_been_setup = False
self._has_menu = False
self._registered_gui = None

AVALON_CONFIG = os.getenv("AVALON_CONFIG", "pype")


def set_workfiles():
    ''' Wrapping function for workfiles launcher '''
    from avalon.tools import workfiles

    # import session to get project dir
    S = avalon.Session
    active_project_root = os.path.normpath(
        os.path.join(S['AVALON_PROJECTS'], S['AVALON_PROJECT'])
    )
    workdir = os.environ["AVALON_WORKDIR"]

    # show workfile gui
    workfiles.show(workdir)

    # getting project
    project = hiero.core.projects()[-1]

    # set project root with backward compatibility
    try:
        project.setProjectDirectory(active_project_root)
    except Exception:
        # old way of seting it
        project.setProjectRoot(active_project_root)

    # get project data from avalon db
    project_data = pype.get_project()["data"]

    log.info("project_data: {}".format(project_data))

    # get format and fps property from avalon db on project
    width = project_data["resolutionWidth"]
    height = project_data["resolutionHeight"]
    pixel_aspect = project_data["pixelAspect"]
    fps = project_data['fps']
    format_name = project_data['code']

    # create new format in hiero project
    format = hiero.core.Format(width, height, pixel_aspect, format_name)
    project.setOutputFormat(format)

    # set fps to hiero project
    project.setFramerate(fps)

    # TODO: add auto colorspace set from project drop
    log.info("Project property has been synchronised with Avalon db")


def reload_config():
    """Attempt to reload pipeline at run-time.

    CAUTION: This is primarily for development and debugging purposes.

    """

    import importlib

    for module in (
        "avalon",
        "avalon.lib",
        "avalon.pipeline",
        "pyblish",
        "pyblish_lite",
        "pypeapp",
        "{}.api".format(AVALON_CONFIG),
        "{}.templates".format(AVALON_CONFIG),
        "{}.nukestudio.lib".format(AVALON_CONFIG),
        "{}.nukestudio.menu".format(AVALON_CONFIG),
        "{}.nukestudio.tags".format(AVALON_CONFIG)
    ):
        log.info("Reloading module: {}...".format(module))
        try:
            module = importlib.import_module(module)
            reload(module)
        except Exception as e:
            log.warning("Cannot reload module: {}".format(e))
            importlib.reload(module)


def setup(console=False, port=None, menu=True):
    """Setup integration

    Registers Pyblish for Hiero plug-ins and appends an item to the File-menu

    Arguments:
        console (bool): Display console with GUI
        port (int, optional): Port from which to start looking for an
            available port to connect with Pyblish QML, default
            provided by Pyblish Integration.
        menu (bool, optional): Display file menu in Hiero.
    """

    if self._has_been_setup:
        teardown()

    add_submission()

    if menu:
        add_to_filemenu()
        self._has_menu = True

    self._has_been_setup = True
    print("pyblish: Loaded successfully.")


def show():
    """Try showing the most desirable GUI
    This function cycles through the currently registered
    graphical user interfaces, if any, and presents it to
    the user.
    """

    return (_discover_gui() or _show_no_gui)()


def _discover_gui():
    """Return the most desirable of the currently registered GUIs"""

    # Prefer last registered
    guis = reversed(pyblish.api.registered_guis())

    for gui in list(guis) + ["pyblish_lite"]:
        try:
            gui = __import__(gui).show
        except (ImportError, AttributeError):
            continue
        else:
            return gui


def teardown():
    """Remove integration"""
    if not self._has_been_setup:
        return

    if self._has_menu:
        remove_from_filemenu()
        self._has_menu = False

    self._has_been_setup = False
    print("pyblish: Integration torn down successfully")


def remove_from_filemenu():
    raise NotImplementedError("Implement me please.")


def add_to_filemenu():
    PublishAction()


class PyblishSubmission(hiero.exporters.FnSubmission.Submission):

    def __init__(self):
        hiero.exporters.FnSubmission.Submission.__init__(self)

    def addToQueue(self):
        # Add submission to Hiero module for retrieval in plugins.
        hiero.submission = self
        show()


def add_submission():
    registry = hiero.core.taskRegistry
    registry.addSubmission("Pyblish", PyblishSubmission)


class PublishAction(QtWidgets.QAction):
    """
    Action with is showing as menu item
    """

    def __init__(self):
        QtWidgets.QAction.__init__(self, "Publish", None)
        self.triggered.connect(self.publish)

        for interest in ["kShowContextMenu/kTimeline",
                         "kShowContextMenukBin",
                         "kShowContextMenu/kSpreadsheet"]:
            hiero.core.events.registerInterest(interest, self.eventHandler)

        self.setShortcut("Ctrl+Alt+P")

    def publish(self):
        # Removing "submission" attribute from hiero module, to prevent tasks
        # from getting picked up when not using the "Export" dialog.
        if hasattr(hiero, "submission"):
            del hiero.submission
        show()

    def eventHandler(self, event):
        # Add the Menu to the right-click menu
        event.menu.addAction(self)


def _show_no_gui():
    """
    Popup with information about how to register a new GUI
    In the event of no GUI being registered or available,
    this information dialog will appear to guide the user
    through how to get set up with one.
    """

    messagebox = QtWidgets.QMessageBox()
    messagebox.setIcon(messagebox.Warning)
    messagebox.setWindowIcon(QtGui.QIcon(os.path.join(
        os.path.dirname(pyblish.__file__),
        "icons",
        "logo-32x32.svg"))
    )

    spacer = QtWidgets.QWidget()
    spacer.setMinimumSize(400, 0)
    spacer.setSizePolicy(QtWidgets.QSizePolicy.Minimum,
                         QtWidgets.QSizePolicy.Expanding)

    layout = messagebox.layout()
    layout.addWidget(spacer, layout.rowCount(), 0, 1, layout.columnCount())

    messagebox.setWindowTitle("Uh oh")
    messagebox.setText("No registered GUI found.")

    if not pyblish.api.registered_guis():
        messagebox.setInformativeText(
            "In order to show you a GUI, one must first be registered. "
            "Press \"Show details...\" below for information on how to "
            "do that.")

        messagebox.setDetailedText(
            "Pyblish supports one or more graphical user interfaces "
            "to be registered at once, the next acting as a fallback to "
            "the previous."
            "\n"
            "\n"
            "For example, to use Pyblish Lite, first install it:"
            "\n"
            "\n"
            "$ pip install pyblish-lite"
            "\n"
            "\n"
            "Then register it, like so:"
            "\n"
            "\n"
            ">>> import pyblish.api\n"
            ">>> pyblish.api.register_gui(\"pyblish_lite\")"
            "\n"
            "\n"
            "The next time you try running this, Lite will appear."
            "\n"
            "See http://api.pyblish.com/register_gui.html for "
            "more information.")

    else:
        messagebox.setInformativeText(
            "None of the registered graphical user interfaces "
            "could be found."
            "\n"
            "\n"
            "Press \"Show details\" for more information.")

        messagebox.setDetailedText(
            "These interfaces are currently registered."
            "\n"
            "%s" % "\n".join(pyblish.api.registered_guis()))

    messagebox.setStandardButtons(messagebox.Ok)
    messagebox.exec_()


def create_nk(filepath, version, representations, nodes=None, to_timeline=False):
    ''' Creating nuke workfile with particular version with given nodes
    Also it is creating timeline track items as precomps.

    Arguments:
        filepath(str): path to workfile to be created
        version(obj): entity avalon db
        representations(list dict): entities from avalon db
        nodes(list of dict): each key in dict is knob order is important
        to_timeline(type): will build trackItem with metadata

    Returns:
        bool: True if done

    Raises:
        Exception: with traceback

    '''
    import hiero.core
    from avalon.nuke import imprint
    from pype.nuke import (
        reset_frame_range_handles,
        set_colorspace
        )
    # check if the file exists if does then Raise "File exists!"
    if os.path.exists(filepath):
        raise FileExistsError("File already exists: `{}`".format(filepath))

    # if no representations matching then
    #   Raise "no representations to be build"
    if len(representations) == 0:
        raise AttributeError("Missing list of `representations`")

    # check nodes input
    if len(nodes) == 0:
        log.warning("Missing list of `nodes`")

    # create temp nk file
    nuke_script = hiero.core.nuke.ScriptWriter()

    version_data = version.get("data", {})

    if not "frameStart" not in version_data.keys():
        raise AttributeError("Missing attribute of version: `frameStart`")

    # editorial
    first_frame = version_data.get("frameStart")
    last_frame = version_data.get("frameEnd")
    fps = version_data.get("fps")

    # setting
    colorspace = version_data.get("colorspaceScript")
    widht = version_data.get("widht")
    height = version_data.get("height")
    pixel_aspect = version_data.get("pixelAspect")

    # handles
    handle_start = version_data.get("handleStart")
    handle_end = version_data.get("handleEnd")

    # create root node and save all metadata
    root_node = hiero.core.nuke.RootNode(
        first_frame,
        last_frame,
        fps=fps
    )

    # run set colorspace, set framerange, set format
    # set colorspace from 'colorspaceScript'
    # root_node.addProjectSettings(colorspace)

    # add root knob AvalonTab and data + publish knob
    # imprint(root_node, {
    #     "handleStart": int(handle_start),
    #     "handleEnd": int(handle_end)
    #     })

    nuke_script.addNode(root_node)

    write_node = hiero.core.nuke.WriteNode(movie_path.replace("\\", "/"))
    write_node.setKnob("file_type", "mov")
    write_node.setKnob("mov32_audiofile", audio_file.replace("\\", "/"))
    write_node.setKnob("mov32_fps", sequence.framerate())
    nuke_script.addNode(write_node)

    nuke_script.writeToDisk(nukescript_path)




    # create read nodes with Loader plugin from matched representations

    # create subsets in workfile
    for repr in representations:
        subset = repr.get("subset")
        id = repr.get("id")
        data = repr.get("data")

        # check if all variables are filled
        if subset and id and data:
            # check if names from `representations` are in db
            # set mov files for correct colorspace
        else:
            raise KeyError("Missing key in `representation`")



    # Create and connect rendering write
