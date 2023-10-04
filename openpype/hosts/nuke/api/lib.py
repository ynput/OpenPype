import os
from pprint import pformat
import re
import json
import six
import functools
import warnings
import platform
import tempfile
import contextlib
from collections import OrderedDict

import nuke
from qtpy import QtCore, QtWidgets

from openpype.client import (
    get_project,
    get_asset_by_name,
    get_versions,
    get_last_versions,
    get_representations,
)

from openpype.host import HostDirmap
from openpype.tools.utils import host_tools
from openpype.pipeline.workfile.workfile_template_builder import (
    TemplateProfileNotFound
)
from openpype.lib import (
    env_value_to_bool,
    Logger,
    get_version_from_path,
    StringTemplate,
)

from openpype.settings import (
    get_project_settings,
    get_current_project_settings,
)
from openpype.modules import ModulesManager
from openpype.pipeline.template_data import get_template_data_with_names
from openpype.pipeline import (
    get_current_project_name,
    discover_legacy_creator_plugins,
    Anatomy,
    get_current_host_name,
    get_current_project_name,
    get_current_asset_name,
)
from openpype.pipeline.context_tools import (
    get_current_project_asset,
    get_custom_workfile_template_from_session
)
from openpype.pipeline.colorspace import (
    get_imageio_config
)
from openpype.pipeline.workfile import BuildWorkfile
from . import gizmo_menu
from .constants import ASSIST

from .workio import (
    save_file,
    open_file
)

log = Logger.get_logger(__name__)

_NODE_TAB_NAME = "{}".format(os.getenv("AVALON_LABEL") or "Avalon")
AVALON_LABEL = os.getenv("AVALON_LABEL") or "Avalon"
AVALON_TAB = "{}".format(AVALON_LABEL)
AVALON_DATA_GROUP = "{}DataGroup".format(AVALON_LABEL.capitalize())
EXCLUDED_KNOB_TYPE_ON_READ = (
    20,  # Tab Knob
    26,  # Text Knob (But for backward compatibility, still be read
         #  if value is not an empty string.)
)
JSON_PREFIX = "JSON:::"
ROOT_DATA_KNOB = "publish_context"
INSTANCE_DATA_KNOB = "publish_instance"


class DeprecatedWarning(DeprecationWarning):
    pass


def deprecated(new_destination):
    """Mark functions as deprecated.

    It will result in a warning being emitted when the function is used.
    """

    func = None
    if callable(new_destination):
        func = new_destination
        new_destination = None

    def _decorator(decorated_func):
        if new_destination is None:
            warning_message = (
                " Please check content of deprecated function to figure out"
                " possible replacement."
            )
        else:
            warning_message = " Please replace your usage with '{}'.".format(
                new_destination
            )

        @functools.wraps(decorated_func)
        def wrapper(*args, **kwargs):
            warnings.simplefilter("always", DeprecatedWarning)
            warnings.warn(
                (
                    "Call to deprecated function '{}'"
                    "\nFunction was moved or removed.{}"
                ).format(decorated_func.__name__, warning_message),
                category=DeprecatedWarning,
                stacklevel=4
            )
            return decorated_func(*args, **kwargs)
        return wrapper

    if func is None:
        return _decorator
    return _decorator(func)


class Context:
    main_window = None
    context_label = None
    project_name = os.getenv("AVALON_PROJECT")
    # Workfile related code
    workfiles_launched = False
    workfiles_tool_timer = None

    # Seems unused
    _project_doc = None


def get_main_window():
    """Acquire Nuke's main window"""
    if Context.main_window is None:

        top_widgets = QtWidgets.QApplication.topLevelWidgets()
        name = "Foundry::UI::DockMainWindow"
        for widget in top_widgets:
            if (
                widget.inherits("QMainWindow")
                and widget.metaObject().className() == name
            ):
                Context.main_window = widget
                break
    return Context.main_window


def set_node_data(node, knobname, data):
    """Write data to node invisible knob

    Will create new in case it doesn't exists
    or update the one already created.

    Args:
        node (nuke.Node): node object
        knobname (str): knob name
        data (dict): data to be stored in knob
    """
    # if exists then update data
    if knobname in node.knobs():
        log.debug("Updating knobname `{}` on node `{}`".format(
            knobname, node.name()
        ))
        update_node_data(node, knobname, data)
        return

    log.debug("Creating knobname `{}` on node `{}`".format(
        knobname, node.name()
    ))
    # else create new
    knob_value = JSON_PREFIX + json.dumps(data)
    knob = nuke.String_Knob(knobname)
    knob.setValue(knob_value)
    knob.setFlag(nuke.INVISIBLE)
    node.addKnob(knob)


def get_node_data(node, knobname):
    """Read data from node.

    Args:
        node (nuke.Node): node object
        knobname (str): knob name

    Returns:
        dict: data stored in knob
    """
    if knobname not in node.knobs():
        return

    rawdata = node[knobname].getValue()
    if (
        isinstance(rawdata, six.string_types)
        and rawdata.startswith(JSON_PREFIX)
    ):
        try:
            return json.loads(rawdata[len(JSON_PREFIX):])
        except json.JSONDecodeError:
            return


def update_node_data(node, knobname, data):
    """Update already present data.

    Args:
        node (nuke.Node): node object
        knobname (str): knob name
        data (dict): data to update knob value
    """
    knob = node[knobname]
    node_data = get_node_data(node, knobname) or {}
    node_data.update(data)
    knob_value = JSON_PREFIX + json.dumps(node_data)
    knob.setValue(knob_value)


class Knobby(object):
    """[DEPRECATED] For creating knob which it's type isn't
                    mapped in `create_knobs`

    Args:
        type (string): Nuke knob type name
        value: Value to be set with `Knob.setValue`, put `None` if not required
        flags (list, optional): Knob flags to be set with `Knob.setFlag`
        *args: Args other than knob name for initializing knob class

    """

    def __init__(self, type, value, flags=None, *args):
        self.type = type
        self.value = value
        self.flags = flags or []
        self.args = args

    def create(self, name, nice=None):
        knob_cls = getattr(nuke, self.type)
        knob = knob_cls(name, nice, *self.args)
        if self.value is not None:
            knob.setValue(self.value)
        for flag in self.flags:
            knob.setFlag(flag)
        return knob

    @staticmethod
    def nice_naming(key):
        """Convert camelCase name into UI Display Name"""
        words = re.findall('[A-Z][^A-Z]*', key[0].upper() + key[1:])
        return " ".join(words)


def create_knobs(data, tab=None):
    """Create knobs by data

    Depending on the type of each dict value and creates the correct Knob.

    Mapped types:
        bool: nuke.Boolean_Knob
        int: nuke.Int_Knob
        float: nuke.Double_Knob
        list: nuke.Enumeration_Knob
        six.string_types: nuke.String_Knob

        dict: If it's a nested dict (all values are dict), will turn into
            A tabs group. Or just a knobs group.

    Args:
        data (dict): collection of attributes and their value
        tab (string, optional): Knobs' tab name

    Returns:
        list: A list of `nuke.Knob` objects

    """
    def nice_naming(key):
        """Convert camelCase name into UI Display Name"""
        words = re.findall('[A-Z][^A-Z]*', key[0].upper() + key[1:])
        return " ".join(words)

    # Turn key-value pairs into knobs
    knobs = list()

    if tab:
        knobs.append(nuke.Tab_Knob(tab))

    for key, value in data.items():
        # Knob name
        if isinstance(key, tuple):
            name, nice = key
        else:
            name, nice = key, nice_naming(key)

        # Create knob by value type
        if isinstance(value, Knobby):
            knobby = value
            knob = knobby.create(name, nice)

        elif isinstance(value, float):
            knob = nuke.Double_Knob(name, nice)
            knob.setValue(value)

        elif isinstance(value, bool):
            knob = nuke.Boolean_Knob(name, nice)
            knob.setValue(value)
            knob.setFlag(nuke.STARTLINE)

        elif isinstance(value, int):
            knob = nuke.Int_Knob(name, nice)
            knob.setValue(value)

        elif isinstance(value, six.string_types):
            knob = nuke.String_Knob(name, nice)
            knob.setValue(value)

        elif isinstance(value, list):
            knob = nuke.Enumeration_Knob(name, nice, value)

        elif isinstance(value, dict):
            if all(isinstance(v, dict) for v in value.values()):
                # Create a group of tabs
                begain = nuke.BeginTabGroup_Knob()
                end = nuke.EndTabGroup_Knob()
                begain.setName(name)
                end.setName(name + "_End")
                knobs.append(begain)
                for k, v in value.items():
                    knobs += create_knobs(v, tab=k)
                knobs.append(end)
            else:
                # Create a group of knobs
                knobs.append(nuke.Tab_Knob(
                    name, nice, nuke.TABBEGINCLOSEDGROUP))
                knobs += create_knobs(value)
                knobs.append(
                    nuke.Tab_Knob(name + "_End", nice, nuke.TABENDGROUP))
            continue

        else:
            raise TypeError("Unsupported type: %r" % type(value))

        knobs.append(knob)

    return knobs


def imprint(node, data, tab=None):
    """Store attributes with value on node

    Parse user data into Node knobs.
    Use `collections.OrderedDict` to ensure knob order.

    Args:
        node(nuke.Node): node object from Nuke
        data(dict): collection of attributes and their value

    Returns:
        None

    Examples:
        ```
        import nuke
        from openpype.hosts.nuke.api import lib

        node = nuke.createNode("NoOp")
        data = {
            # Regular type of attributes
            "myList": ["x", "y", "z"],
            "myBool": True,
            "myFloat": 0.1,
            "myInt": 5,

            # Creating non-default imprint type of knob
            "MyFilePath": lib.Knobby("File_Knob", "/file/path"),
            "divider": lib.Knobby("Text_Knob", ""),

            # Manual nice knob naming
            ("my_knob", "Nice Knob Name"): "some text",

            # dict type will be created as knob group
            "KnobGroup": {
                "knob1": 5,
                "knob2": "hello",
                "knob3": ["a", "b"],
            },

            # Nested dict will be created as tab group
            "TabGroup": {
                "tab1": {"count": 5},
                "tab2": {"isGood": True},
                "tab3": {"direction": ["Left", "Right"]},
            },
        }
        lib.imprint(node, data, tab="Demo")

        ```

    """
    for knob in create_knobs(data, tab):
        node.addKnob(knob)


@deprecated
def add_publish_knob(node):
    """[DEPRECATED] Add Publish knob to node

    Arguments:
        node (nuke.Node): nuke node to be processed

    Returns:
        node (nuke.Node): processed nuke node

    """
    if "publish" not in node.knobs():
        body = OrderedDict()
        body[("divd", "Publishing")] = Knobby("Text_Knob", '')
        body["publish"] = True
        imprint(node, body)
    return node


@deprecated("openpype.hosts.nuke.api.lib.set_node_data")
def set_avalon_knob_data(node, data=None, prefix="avalon:"):
    """[DEPRECATED] Sets data into nodes's avalon knob

    This function is still used but soon will be deprecated.
    Use `set_node_data` instead.

    Arguments:
        node (nuke.Node): Nuke node to imprint with data,
        data (dict, optional): Data to be imprinted into AvalonTab
        prefix (str, optional): filtering prefix

    Returns:
        node (nuke.Node)

    Examples:
        data = {
            'asset': 'sq020sh0280',
            'family': 'render',
            'subset': 'subsetMain'
        }
    """
    data = data or dict()
    create = OrderedDict()

    tab_name = AVALON_TAB
    editable = ["asset", "subset", "name", "namespace"]

    existed_knobs = node.knobs()

    for key, value in data.items():
        knob_name = prefix + key
        gui_name = key

        if knob_name in existed_knobs:
            # Set value
            try:
                node[knob_name].setValue(value)
            except TypeError:
                node[knob_name].setValue(str(value))
        else:
            # New knob
            name = (knob_name, gui_name)  # Hide prefix on GUI
            if key in editable:
                create[name] = value
            else:
                create[name] = Knobby("String_Knob",
                                      str(value),
                                      flags=[nuke.READ_ONLY])
    if tab_name in existed_knobs:
        tab_name = None
    else:
        tab = OrderedDict()
        warn = Knobby("Text_Knob", "Warning! Do not change following data!")
        divd = Knobby("Text_Knob", "")
        head = [
            (("warn", ""), warn),
            (("divd", ""), divd),
        ]
        tab[AVALON_DATA_GROUP] = OrderedDict(head + list(create.items()))
        create = tab

    imprint(node, create, tab=tab_name)
    return node


@deprecated("openpype.hosts.nuke.api.lib.get_node_data")
def get_avalon_knob_data(node, prefix="avalon:", create=True):
    """[DEPRECATED]  Gets a data from nodes's avalon knob

    This function is still used but soon will be deprecated.
    Use `get_node_data` instead.

    Arguments:
        node (obj): Nuke node to search for data,
        prefix (str, optional): filtering prefix

    Returns:
        data (dict)
    """

    data = {}
    if AVALON_TAB not in node.knobs():
        return data

    # check if lists
    if not isinstance(prefix, list):
        prefix = [prefix]

    # loop prefix
    for p in prefix:
        # check if the node is avalon tracked
        try:
            # check if data available on the node
            test = node[AVALON_DATA_GROUP].value()
            log.debug("Only testing if data available: `{}`".format(test))
        except NameError as e:
            # if it doesn't then create it
            log.debug("Creating avalon knob: `{}`".format(e))
            if create:
                node = set_avalon_knob_data(node)
                return get_avalon_knob_data(node)
            return {}

        # get data from filtered knobs
        data.update({k.replace(p, ''): node[k].value()
                    for k in node.knobs().keys()
                    if p in k})

    return data


@deprecated
def fix_data_for_node_create(data):
    """[DEPRECATED] Fixing data to be used for nuke knobs
    """
    for k, v in data.items():
        if isinstance(v, six.text_type):
            data[k] = str(v)
        if str(v).startswith("0x"):
            data[k] = int(v, 16)
    return data


@deprecated
def add_write_node_legacy(name, **kwarg):
    """[DEPRECATED] Adding nuke write node
    Arguments:
        name (str): nuke node name
        kwarg (attrs): data for nuke knobs
    Returns:
        node (obj): nuke write node
    """
    use_range_limit = kwarg.get("use_range_limit", None)

    w = nuke.createNode(
        "Write",
        "name {}".format(name),
        inpanel=False
    )

    w["file"].setValue(kwarg["file"])

    for k, v in kwarg.items():
        if "frame_range" in k:
            continue
        log.info([k, v])
        try:
            w[k].setValue(v)
        except KeyError as e:
            log.debug(e)
            continue

    if use_range_limit:
        w["use_limit"].setValue(True)
        w["first"].setValue(kwarg["frame_range"][0])
        w["last"].setValue(kwarg["frame_range"][1])

    return w


def add_write_node(name, file_path, knobs, **kwarg):
    """Adding nuke write node

    Arguments:
        name (str): nuke node name
        kwarg (attrs): data for nuke knobs

    Returns:
        node (obj): nuke write node
    """
    use_range_limit = kwarg.get("use_range_limit", None)

    w = nuke.createNode(
        "Write",
        "name {}".format(name),
        inpanel=False
    )

    w["file"].setValue(file_path)

    # finally add knob overrides
    set_node_knobs_from_settings(w, knobs, **kwarg)

    if use_range_limit:
        w["use_limit"].setValue(True)
        w["first"].setValue(kwarg["frame_range"][0])
        w["last"].setValue(kwarg["frame_range"][1])

    return w


def read_avalon_data(node):
    """Return user-defined knobs from given `node`

    Args:
        node (nuke.Node): Nuke node object

    Returns:
        list: A list of nuke.Knob object

    """
    def compat_prefixed(knob_name):
        if knob_name.startswith("avalon:"):
            return knob_name[len("avalon:"):]
        elif knob_name.startswith("ak:"):
            return knob_name[len("ak:"):]

    data = dict()

    pattern = ("(?<=addUserKnob {)"
               "([0-9]*) (\\S*)"  # Matching knob type and knob name
               "(?=[ |}])")
    tcl_script = node.writeKnobs(nuke.WRITE_USER_KNOB_DEFS)
    result = re.search(pattern, tcl_script)

    if result:
        first_user_knob = result.group(2)
        # Collect user knobs from the end of the knob list
        for knob in reversed(node.allKnobs()):
            knob_name = knob.name()
            if not knob_name:
                # Ignore unnamed knob
                continue

            knob_type = nuke.knob(knob.fullyQualifiedName(), type=True)
            value = knob.value()

            if (
                knob_type not in EXCLUDED_KNOB_TYPE_ON_READ or
                # For compating read-only string data that imprinted
                # by `nuke.Text_Knob`.
                (knob_type == 26 and value)
            ):
                key = compat_prefixed(knob_name)
                if key is not None:
                    data[key] = value

            if knob_name == first_user_knob:
                break

    return data


def get_node_path(path, padding=4):
    """Get filename for the Nuke write with padded number as '#'

    Arguments:
        path (str): The path to render to.

    Returns:
        tuple: head, padding, tail (extension)

    Examples:
        >>> get_frame_path("test.exr")
        ('test', 4, '.exr')

        >>> get_frame_path("filename.#####.tif")
        ('filename.', 5, '.tif')

        >>> get_frame_path("foobar##.tif")
        ('foobar', 2, '.tif')

        >>> get_frame_path("foobar_%08d.tif")
        ('foobar_', 8, '.tif')
    """
    filename, ext = os.path.splitext(path)

    # Find a final number group
    if '%' in filename:
        match = re.match('.*?(%[0-9]+d)$', filename)
        if match:
            padding = int(match.group(1).replace('%', '').replace('d', ''))
            # remove number from end since fusion
            # will swap it with the frame number
            filename = filename.replace(match.group(1), '')
    elif '#' in filename:
        match = re.match('.*?(#+)$', filename)

        if match:
            padding = len(match.group(1))
            # remove number from end since fusion
            # will swap it with the frame number
            filename = filename.replace(match.group(1), '')

    return filename, padding, ext


def get_nuke_imageio_settings():
    return get_project_settings(Context.project_name)["nuke"]["imageio"]


@deprecated("openpype.hosts.nuke.api.lib.get_nuke_imageio_settings")
def get_created_node_imageio_setting_legacy(nodeclass, creator, subset):
    '''[DEPRECATED]  Get preset data for dataflow (fileType, compression, bitDepth)
    '''

    assert any([creator, nodeclass]), nuke.message(
        "`{}`: Missing mandatory kwargs `host`, `cls`".format(__file__))

    imageio_nodes = get_nuke_imageio_settings()["nodes"]
    required_nodes = imageio_nodes["requiredNodes"]

    # HACK: for backward compatibility this needs to be optional
    override_nodes = imageio_nodes.get("overrideNodes", [])

    imageio_node = None
    for node in required_nodes:
        log.info(node)
        if (
                nodeclass in node["nukeNodeClass"]
                and creator in node["plugins"]
        ):
            imageio_node = node
            break

    log.debug("__ imageio_node: {}".format(imageio_node))

    # find matching override node
    override_imageio_node = None
    for onode in override_nodes:
        log.info(onode)
        if nodeclass not in node["nukeNodeClass"]:
            continue

        if creator not in node["plugins"]:
            continue

        if (
            onode["subsets"]
            and not any(
                re.search(s.lower(), subset.lower())
                for s in onode["subsets"]
            )
        ):
            continue

        override_imageio_node = onode
        break

    log.debug("__ override_imageio_node: {}".format(override_imageio_node))
    # add overrides to imageio_node
    if override_imageio_node:
        # get all knob names in imageio_node
        knob_names = [k["name"] for k in imageio_node["knobs"]]

        for oknob in override_imageio_node["knobs"]:
            for knob in imageio_node["knobs"]:
                # override matching knob name
                if oknob["name"] == knob["name"]:
                    log.debug(
                        "_ overriding knob: `{}` > `{}`".format(
                            knob, oknob
                        ))
                    if not oknob["value"]:
                        # remove original knob if no value found in oknob
                        imageio_node["knobs"].remove(knob)
                    else:
                        # override knob value with oknob's
                        knob["value"] = oknob["value"]

                # add missing knobs into imageio_node
                if oknob["name"] not in knob_names:
                    log.debug(
                        "_ adding knob: `{}`".format(oknob))
                    imageio_node["knobs"].append(oknob)
                    knob_names.append(oknob["name"])

    log.info("ImageIO node: {}".format(imageio_node))
    return imageio_node


def get_imageio_node_setting(node_class, plugin_name, subset):
    ''' Get preset data for dataflow (fileType, compression, bitDepth)
    '''
    imageio_nodes = get_nuke_imageio_settings()["nodes"]
    required_nodes = imageio_nodes["requiredNodes"]

    imageio_node = None
    for node in required_nodes:
        log.info(node)
        if (
                node_class in node["nukeNodeClass"]
                and plugin_name in node["plugins"]
        ):
            imageio_node = node
            break

    log.debug("__ imageio_node: {}".format(imageio_node))

    if not imageio_node:
        return

    # find overrides and update knobs with them
    get_imageio_node_override_setting(
        node_class,
        plugin_name,
        subset,
        imageio_node["knobs"]
    )

    log.info("ImageIO node: {}".format(imageio_node))
    return imageio_node


def get_imageio_node_override_setting(
    node_class, plugin_name, subset, knobs_settings
):
    ''' Get imageio node overrides from settings
    '''
    imageio_nodes = get_nuke_imageio_settings()["nodes"]
    override_nodes = imageio_nodes["overrideNodes"]

    # find matching override node
    override_imageio_node = None
    for onode in override_nodes:
        log.debug("__ onode: {}".format(onode))
        log.debug("__ subset: {}".format(subset))
        if node_class not in onode["nukeNodeClass"]:
            continue

        if plugin_name not in onode["plugins"]:
            continue

        if (
            onode["subsets"]
            and not any(
                re.search(s.lower(), subset.lower())
                for s in onode["subsets"]
            )
        ):
            continue

        override_imageio_node = onode
        break

    log.debug("__ override_imageio_node: {}".format(override_imageio_node))
    # add overrides to imageio_node
    if override_imageio_node:
        # get all knob names in imageio_node
        knob_names = [k["name"] for k in knobs_settings]

        for oknob in override_imageio_node["knobs"]:
            for knob in knobs_settings:
                # override matching knob name
                if oknob["name"] == knob["name"]:
                    log.debug(
                        "_ overriding knob: `{}` > `{}`".format(
                            knob, oknob
                        ))
                    if not oknob["value"]:
                        # remove original knob if no value found in oknob
                        knobs_settings.remove(knob)
                    else:
                        # override knob value with oknob's
                        knob["value"] = oknob["value"]

                # add missing knobs into imageio_node
                if oknob["name"] not in knob_names:
                    log.debug(
                        "_ adding knob: `{}`".format(oknob))
                    knobs_settings.append(oknob)
                    knob_names.append(oknob["name"])

    return knobs_settings


def get_imageio_input_colorspace(filename):
    ''' Get input file colorspace based on regex in settings.
    '''
    imageio_regex_inputs = (
        get_nuke_imageio_settings()["regexInputs"]["inputs"])

    preset_clrsp = None
    for regexInput in imageio_regex_inputs:
        if bool(re.search(regexInput["regex"], filename)):
            preset_clrsp = str(regexInput["colorspace"])

    return preset_clrsp


def get_view_process_node():
    reset_selection()

    ipn_node = None
    for v_ in nuke.allNodes(filter="Viewer"):
        ipn = v_['input_process_node'].getValue()
        ipn_node = nuke.toNode(ipn)

        # skip if no input node is set
        if not ipn:
            continue

        if ipn == "VIEWER_INPUT" and not ipn_node:
            # since it is set by default we can ignore it
            # nobody usually use this but use it if
            # it exists in nodes
            continue

        if not ipn_node:
            # in case a Viewer node is transferred from
            # different workfile with old values
            raise NameError((
                "Input process node name '{}' set in "
                "Viewer '{}' is doesn't exists in nodes"
            ).format(ipn, v_.name()))

        ipn_node.setSelected(True)

    if ipn_node:
        return duplicate_node(ipn_node)


def on_script_load():
    ''' Callback for ffmpeg support
    '''
    if nuke.env["LINUX"]:
        nuke.tcl('load ffmpegReader')
        nuke.tcl('load ffmpegWriter')
    else:
        nuke.tcl('load movReader')
        nuke.tcl('load movWriter')


def check_inventory_versions():
    """
    Actual version idetifier of Loaded containers

    Any time this function is run it will check all nodes and filter only
    Loader nodes for its version. It will get all versions from database
    and check if the node is having actual version. If not then it will color
    it to red.
    """
    from .pipeline import parse_container

    # get all Loader nodes by avalon attribute metadata
    node_with_repre_id = []
    repre_ids = set()
    # Find all containers and collect it's node and representation ids
    for node in nuke.allNodes():
        container = parse_container(node)

        if container:
            node = nuke.toNode(container["objectName"])
            avalon_knob_data = read_avalon_data(node)
            repre_id = avalon_knob_data["representation"]

            repre_ids.add(repre_id)
            node_with_repre_id.append((node, repre_id))

    # Skip if nothing was found
    if not repre_ids:
        return

    project_name = get_current_project_name()
    # Find representations based on found containers
    repre_docs = get_representations(
        project_name,
        representation_ids=repre_ids,
        fields=["_id", "parent"]
    )
    # Store representations by id and collect version ids
    repre_docs_by_id = {}
    version_ids = set()
    for repre_doc in repre_docs:
        # Use stringed representation id to match value in containers
        repre_id = str(repre_doc["_id"])
        repre_docs_by_id[repre_id] = repre_doc
        version_ids.add(repre_doc["parent"])

    version_docs = get_versions(
        project_name, version_ids, fields=["_id", "name", "parent"]
    )
    # Store versions by id and collect subset ids
    version_docs_by_id = {}
    subset_ids = set()
    for version_doc in version_docs:
        version_docs_by_id[version_doc["_id"]] = version_doc
        subset_ids.add(version_doc["parent"])

    # Query last versions based on subset ids
    last_versions_by_subset_id = get_last_versions(
        project_name, subset_ids=subset_ids, fields=["_id", "parent"]
    )

    # Loop through collected container nodes and their representation ids
    for item in node_with_repre_id:
        # Some python versions of nuke can't unfold tuple in for loop
        node, repre_id = item
        repre_doc = repre_docs_by_id.get(repre_id)
        # Failsafe for not finding the representation.
        if not repre_doc:
            log.warning((
                "Could not find the representation on node \"{}\""
            ).format(node.name()))
            continue

        version_id = repre_doc["parent"]
        version_doc = version_docs_by_id.get(version_id)
        if not version_doc:
            log.warning((
                "Could not find the version on node \"{}\""
            ).format(node.name()))
            continue

        # Get last version based on subset id
        subset_id = version_doc["parent"]
        last_version = last_versions_by_subset_id[subset_id]
        # Check if last version is same as current version
        if last_version["_id"] == version_doc["_id"]:
            color_value = "0x4ecd25ff"
        else:
            color_value = "0xd84f20ff"
        node["tile_color"].setValue(int(color_value, 16))


def writes_version_sync():
    ''' Callback synchronizing version of publishable write nodes
    '''
    try:
        rootVersion = get_version_from_path(nuke.root().name())
        padding = len(rootVersion)
        new_version = "v" + str("{" + ":0>{}".format(padding) + "}").format(
            int(rootVersion)
        )
        log.debug("new_version: {}".format(new_version))
    except Exception:
        return

    for each in nuke.allNodes(filter="Write"):
        # check if the node is avalon tracked
        if _NODE_TAB_NAME not in each.knobs():
            continue

        avalon_knob_data = read_avalon_data(each)

        try:
            if avalon_knob_data["families"] not in ["render"]:
                log.debug(avalon_knob_data["families"])
                continue

            node_file = each["file"].value()

            node_version = "v" + get_version_from_path(node_file)
            log.debug("node_version: {}".format(node_version))

            node_new_file = node_file.replace(node_version, new_version)
            each["file"].setValue(node_new_file)
            if not os.path.isdir(os.path.dirname(node_new_file)):
                log.warning("Path does not exist! I am creating it.")
                os.makedirs(os.path.dirname(node_new_file))
        except Exception as e:
            log.warning(
                "Write node: `{}` has no version in path: {}".format(
                    each.name(), e))


def version_up_script():
    ''' Raising working script's version
    '''
    import nukescripts
    nukescripts.script_and_write_nodes_version_up()


def check_subsetname_exists(nodes, subset_name):
    """
    Checking if node is not already created to secure there is no duplicity

    Arguments:
        nodes (list): list of nuke.Node objects
        subset_name (str): name we try to find

    Returns:
        bool: True of False
    """
    return next((True for n in nodes
                 if subset_name in read_avalon_data(n).get("subset", "")),
                False)


def get_render_path(node):
    ''' Generate Render path from presets regarding avalon knob data
    '''
    avalon_knob_data = read_avalon_data(node)

    nuke_imageio_writes = get_imageio_node_setting(
        node_class=avalon_knob_data["families"],
        plugin_name=avalon_knob_data["creator"],
        subset=avalon_knob_data["subset"]
    )

    data = {
        "avalon": avalon_knob_data,
        "nuke_imageio_writes": nuke_imageio_writes
    }

    anatomy_filled = format_anatomy(data)
    return anatomy_filled["render"]["path"].replace("\\", "/")


def format_anatomy(data):
    ''' Helping function for formatting of anatomy paths

    Arguments:
        data (dict): dictionary with attributes used for formatting

    Return:
        path (str)
    '''
    anatomy = Anatomy()
    log.debug("__ anatomy.templates: {}".format(anatomy.templates))

    padding = None
    if "frame_padding" in anatomy.templates.keys():
        padding = int(anatomy.templates["frame_padding"])
    elif "render" in anatomy.templates.keys():
        padding = int(
            anatomy.templates["render"].get(
                "frame_padding"
            )
        )

    version = data.get("version", None)
    if not version:
        file = script_name()
        data["version"] = get_version_from_path(file)

    project_name = anatomy.project_name
    asset_name = data["asset"]
    task_name = data["task"]
    host_name = get_current_host_name()
    context_data = get_template_data_with_names(
        project_name, asset_name, task_name, host_name
    )
    data.update(context_data)
    data.update({
        "subset": data["subset"],
        "family": data["family"],
        "frame": "#" * padding,
    })
    return anatomy.format(data)


def script_name():
    ''' Returns nuke script path
    '''
    return nuke.root().knob("name").value()


def add_button_write_to_read(node):
    name = "createReadNode"
    label = "Read From Rendered"
    value = "import write_to_read;\
        write_to_read.write_to_read(nuke.thisNode(), allow_relative=False)"
    knob = nuke.PyScript_Knob(name, label, value)
    knob.clearFlag(nuke.STARTLINE)
    node.addKnob(knob)


def add_button_clear_rendered(node, path):
    name = "clearRendered"
    label = "Clear Rendered"
    value = "import clear_rendered;\
        clear_rendered.clear_rendered(\"{}\")".format(path)
    knob = nuke.PyScript_Knob(name, label, value)
    node.addKnob(knob)


def create_prenodes(
    prev_node,
    nodes_setting,
    plugin_name=None,
    subset=None,
    **kwargs
):
    last_node = None
    for_dependency = {}
    for name, node in nodes_setting.items():
        # get attributes
        nodeclass = node["nodeclass"]
        knobs = node["knobs"]

        # create node
        now_node = nuke.createNode(
            nodeclass,
            "name {}".format(name),
            inpanel=False
        )

        # add for dependency linking
        for_dependency[name] = {
            "node": now_node,
            "dependent": node["dependent"]
        }

        if all([plugin_name, subset]):
            # find imageio overrides
            get_imageio_node_override_setting(
                now_node.Class(),
                plugin_name,
                subset,
                knobs
            )

        # add data to knob
        set_node_knobs_from_settings(now_node, knobs, **kwargs)

        # switch actual node to previous
        last_node = now_node

    for _node_name, node_prop in for_dependency.items():
        if not node_prop["dependent"]:
            node_prop["node"].setInput(
                0, prev_node)
        elif node_prop["dependent"] in for_dependency:
            _prev_node = for_dependency[node_prop["dependent"]]["node"]
            node_prop["node"].setInput(
                0, _prev_node)
        else:
            log.warning("Dependency has wrong name of node: {}".format(
                node_prop
            ))

    return last_node


def create_write_node(
    name,
    data,
    input=None,
    prenodes=None,
    linked_knobs=None,
    **kwargs
):
    ''' Creating write node which is group node

    Arguments:
        name (str): name of node
        data (dict): creator write instance data
        input (node)[optional]: selected node to connect to
        prenodes (dict)[optional]:
            nodes to be created before write with dependency
        review (bool)[optional]: adding review knob
        farm (bool)[optional]: rendering workflow target
        kwargs (dict)[optional]: additional key arguments for formatting

    Example:
        prenodes = {
            "nodeName": {
                "nodeclass": "Reformat",
                "dependent": [
                    following_node_01,
                    ...
                ],
                "knobs": [
                    {
                        "type": "text",
                        "name": "knobname",
                        "value": "knob value"
                    },
                    ...
                ]
            },
            ...
        }


    Return:
        node (obj): group node with avalon data as Knobs
    '''
    prenodes = prenodes or {}

    # filtering variables
    plugin_name = data["creator"]
    subset = data["subset"]

    # get knob settings for write node
    imageio_writes = get_imageio_node_setting(
        node_class="Write",
        plugin_name=plugin_name,
        subset=subset
    )

    for knob in imageio_writes["knobs"]:
        if knob["name"] == "file_type":
            ext = knob["value"]

    data.update({
        "imageio_writes": imageio_writes,
        "ext": ext
    })
    anatomy_filled = format_anatomy(data)

    # build file path to workfiles
    fdir = str(anatomy_filled["work"]["folder"]).replace("\\", "/")
    data["work"] = fdir
    fpath = StringTemplate(data["fpath_template"]).format_strict(data)

    # create directory
    if not os.path.isdir(os.path.dirname(fpath)):
        log.warning("Path does not exist! I am creating it.")
        os.makedirs(os.path.dirname(fpath))

    GN = nuke.createNode("Group", "name {}".format(name))

    prev_node = None
    with GN:
        if input:
            input_name = str(input.name()).replace(" ", "")
            # if connected input node was defined
            prev_node = nuke.createNode(
                "Input",
                "name {}".format(input_name),
                inpanel=False
            )
        else:
            # generic input node connected to nothing
            prev_node = nuke.createNode(
                "Input",
                "name {}".format("rgba"),
                inpanel=False
            )

        # creating pre-write nodes `prenodes`
        last_prenode = create_prenodes(
            prev_node,
            prenodes,
            plugin_name,
            subset,
            **kwargs
        )
        if last_prenode:
            prev_node = last_prenode

        # creating write node
        write_node = now_node = add_write_node(
            "inside_{}".format(name),
            fpath,
            imageio_writes["knobs"],
            **data
        )
        # connect to previous node
        now_node.setInput(0, prev_node)

        # switch actual node to previous
        prev_node = now_node

        now_node = nuke.createNode("Output", "name Output1", inpanel=False)

        # connect to previous node
        now_node.setInput(0, prev_node)

    # add divider
    GN.addKnob(nuke.Text_Knob('', 'Rendering'))

    # Add linked knobs.
    linked_knob_names = []

    # add input linked knobs and create group only if any input
    if linked_knobs:
        linked_knob_names.append("_grp-start_")
        linked_knob_names.extend(linked_knobs)
        linked_knob_names.append("_grp-end_")

    linked_knob_names.append("Render")

    for _k_name in linked_knob_names:
        if "_grp-start_" in _k_name:
            knob = nuke.Tab_Knob(
                "rnd_attr", "Rendering attributes", nuke.TABBEGINCLOSEDGROUP)
            GN.addKnob(knob)
        elif "_grp-end_" in _k_name:
            knob = nuke.Tab_Knob(
                "rnd_attr_end", "Rendering attributes", nuke.TABENDGROUP)
            GN.addKnob(knob)
        else:
            if "___" in _k_name:
                # add divider
                GN.addKnob(nuke.Text_Knob(""))
            else:
                # add linked knob by _k_name
                link = nuke.Link_Knob("")
                link.makeLink(write_node.name(), _k_name)
                link.setName(_k_name)

                # make render
                if "Render" in _k_name:
                    link.setLabel("Render Local")
                link.setFlag(0x1000)
                GN.addKnob(link)

    # adding write to read button
    add_button_write_to_read(GN)

    # adding write to read button
    add_button_clear_rendered(GN, os.path.dirname(fpath))

    # set tile color
    tile_color = next(
        iter(
            k["value"] for k in imageio_writes["knobs"]
            if "tile_color" in k["name"]
        ), [255, 0, 0, 255]
    )
    GN["tile_color"].setValue(
        color_gui_to_int(tile_color))

    return GN


@deprecated("openpype.hosts.nuke.api.lib.create_write_node")
def create_write_node_legacy(
    name, data, input=None, prenodes=None,
    review=True, linked_knobs=None, farm=True
):
    ''' Creating write node which is group node

    Arguments:
        name (str): name of node
        data (dict): data to be imprinted
        input (node): selected node to connect to
        prenodes (list, optional): list of lists, definitions for nodes
                                to be created before write
        review (bool): adding review knob

    Example:
        prenodes = [
            {
                "nodeName": {
                    "class": ""  # string
                    "knobs": [
                        ("knobName": value),
                        ...
                    ],
                    "dependent": [
                        following_node_01,
                        ...
                    ]
                }
            },
            ...
        ]

    Return:
        node (obj): group node with avalon data as Knobs
    '''
    knob_overrides = data.get("knobs", [])
    nodeclass = data["nodeclass"]
    creator = data["creator"]
    subset = data["subset"]

    imageio_writes = get_created_node_imageio_setting_legacy(
        nodeclass, creator, subset
    )
    for knob in imageio_writes["knobs"]:
        if knob["name"] == "file_type":
            representation = knob["value"]

    host_name = get_current_host_name()
    try:
        data.update({
            "app": host_name,
            "imageio_writes": imageio_writes,
            "representation": representation,
        })
        anatomy_filled = format_anatomy(data)

    except Exception as e:
        msg = "problem with resolving anatomy template: {}".format(e)
        log.error(msg)
        nuke.message(msg)

    # build file path to workfiles
    fdir = str(anatomy_filled["work"]["folder"]).replace("\\", "/")
    fpath = data["fpath_template"].format(
        work=fdir, version=data["version"], subset=data["subset"],
        frame=data["frame"],
        ext=representation
    )

    # create directory
    if not os.path.isdir(os.path.dirname(fpath)):
        log.warning("Path does not exist! I am creating it.")
        os.makedirs(os.path.dirname(fpath))

    _data = OrderedDict({
        "file": fpath
    })

    # adding dataflow template
    log.debug("imageio_writes: `{}`".format(imageio_writes))
    for knob in imageio_writes["knobs"]:
        _data[knob["name"]] = knob["value"]

    _data = fix_data_for_node_create(_data)

    log.debug("_data: `{}`".format(_data))

    if "frame_range" in data.keys():
        _data["frame_range"] = data.get("frame_range", None)
        log.debug("_data[frame_range]: `{}`".format(_data["frame_range"]))

    GN = nuke.createNode("Group", "name {}".format(name))

    prev_node = None
    with GN:
        if input:
            input_name = str(input.name()).replace(" ", "")
            # if connected input node was defined
            prev_node = nuke.createNode(
                "Input", "name {}".format(input_name))
        else:
            # generic input node connected to nothing
            prev_node = nuke.createNode(
                "Input",
                "name {}".format("rgba"),
                inpanel=False
            )
        # creating pre-write nodes `prenodes`
        if prenodes:
            for node in prenodes:
                # get attributes
                pre_node_name = node["name"]
                klass = node["class"]
                knobs = node["knobs"]
                dependent = node["dependent"]

                # create node
                now_node = nuke.createNode(
                    klass,
                    "name {}".format(pre_node_name),
                    inpanel=False
                )

                # add data to knob
                for _knob in knobs:
                    knob, value = _knob
                    try:
                        now_node[knob].value()
                    except NameError:
                        log.warning(
                            "knob `{}` does not exist on node `{}`".format(
                                knob, now_node["name"].value()
                            ))
                        continue

                    if not knob and not value:
                        continue

                    log.info((knob, value))

                    if isinstance(value, str):
                        if "[" in value:
                            now_node[knob].setExpression(value)
                    else:
                        now_node[knob].setValue(value)

                # connect to previous node
                if dependent:
                    if isinstance(dependent, (tuple or list)):
                        for i, node_name in enumerate(dependent):
                            input_node = nuke.createNode(
                                "Input",
                                "name {}".format(node_name),
                                inpanel=False
                            )
                            now_node.setInput(1, input_node)

                    elif isinstance(dependent, str):
                        input_node = nuke.createNode(
                            "Input",
                            "name {}".format(node_name),
                            inpanel=False
                        )
                        now_node.setInput(0, input_node)

                else:
                    now_node.setInput(0, prev_node)

                # switch actual node to previous
                prev_node = now_node

        # creating write node

        write_node = now_node = add_write_node_legacy(
            "inside_{}".format(name),
            **_data
        )
        # connect to previous node
        now_node.setInput(0, prev_node)

        # switch actual node to previous
        prev_node = now_node

        now_node = nuke.createNode("Output", "name Output1", inpanel=False)

        # connect to previous node
        now_node.setInput(0, prev_node)

    # imprinting group node
    set_avalon_knob_data(GN, data["avalon"])
    add_publish_knob(GN)
    add_rendering_knobs(GN, farm)

    if review:
        add_review_knob(GN)

    # add divider
    GN.addKnob(nuke.Text_Knob('', 'Rendering'))

    # Add linked knobs.
    linked_knob_names = []

    # add input linked knobs and create group only if any input
    if linked_knobs:
        linked_knob_names.append("_grp-start_")
        linked_knob_names.extend(linked_knobs)
        linked_knob_names.append("_grp-end_")

    linked_knob_names.append("Render")

    for _k_name in linked_knob_names:
        if "_grp-start_" in _k_name:
            knob = nuke.Tab_Knob(
                "rnd_attr", "Rendering attributes", nuke.TABBEGINCLOSEDGROUP)
            GN.addKnob(knob)
        elif "_grp-end_" in _k_name:
            knob = nuke.Tab_Knob(
                "rnd_attr_end", "Rendering attributes", nuke.TABENDGROUP)
            GN.addKnob(knob)
        else:
            if "___" in _k_name:
                # add divider
                GN.addKnob(nuke.Text_Knob(""))
            else:
                # add linked knob by _k_name
                link = nuke.Link_Knob("")
                link.makeLink(write_node.name(), _k_name)
                link.setName(_k_name)

                # make render
                if "Render" in _k_name:
                    link.setLabel("Render Local")
                link.setFlag(0x1000)
                GN.addKnob(link)

    # adding write to read button
    add_button_write_to_read(GN)

    # adding write to read button
    add_button_clear_rendered(GN, os.path.dirname(fpath))

    # Deadline tab.
    add_deadline_tab(GN)

    # open the our Tab as default
    GN[_NODE_TAB_NAME].setFlag(0)

    # set tile color
    tile_color = _data.get("tile_color", "0xff0000ff")
    GN["tile_color"].setValue(tile_color)

    # override knob values from settings
    for knob in knob_overrides:
        knob_type = knob["type"]
        knob_name = knob["name"]
        knob_value = knob["value"]
        if knob_name not in GN.knobs():
            continue
        if not knob_value:
            continue

        # set correctly knob types
        if knob_type == "string":
            knob_value = str(knob_value)
        if knob_type == "number":
            knob_value = int(knob_value)
        if knob_type == "decimal_number":
            knob_value = float(knob_value)
        if knob_type == "bool":
            knob_value = bool(knob_value)
        if knob_type in ["2d_vector", "3d_vector", "color", "box"]:
            knob_value = list(knob_value)

        GN[knob_name].setValue(knob_value)

    return GN


def set_node_knobs_from_settings(node, knob_settings, **kwargs):
    """ Overriding knob values from settings

    Using `schema_nuke_knob_inputs` for knob type definitions.

    Args:
        node (nuke.Node): nuke node
        knob_settings (list): list of dict. Keys are `type`, `name`, `value`
        kwargs (dict)[optional]: keys for formattable knob settings
    """
    for knob in knob_settings:
        log.debug("__ knob: {}".format(pformat(knob)))
        knob_type = knob["type"]
        knob_name = knob["name"]

        if knob_name not in node.knobs():
            continue

        if knob_type == "expression":
            knob_expression = knob["expression"]
            node[knob_name].setExpression(
                knob_expression
            )
            continue

        # first deal with formattable knob settings
        if knob_type == "formatable":
            template = knob["template"]
            to_type = knob["to_type"]
            try:
                _knob_value = template.format(
                    **kwargs
                )
            except KeyError as msg:
                raise KeyError(
                    "Not able to format expression: {}".format(msg))

            # convert value to correct type
            if to_type == "2d_vector":
                knob_value = _knob_value.split(";").split(",")
            else:
                knob_value = _knob_value

            knob_type = to_type

        else:
            knob_value = knob["value"]

        if not knob_value:
            continue

        knob_value = convert_knob_value_to_correct_type(
            knob_type, knob_value)

        node[knob_name].setValue(knob_value)


def convert_knob_value_to_correct_type(knob_type, knob_value):
    # first convert string types to string
    # just to ditch unicode
    if isinstance(knob_value, six.text_type):
        knob_value = str(knob_value)

    # set correctly knob types
    if knob_type == "bool":
        knob_value = bool(knob_value)
    elif knob_type == "decimal_number":
        knob_value = float(knob_value)
    elif knob_type == "number":
        knob_value = int(knob_value)
    elif knob_type == "text":
        knob_value = knob_value
    elif knob_type == "color_gui":
        knob_value = color_gui_to_int(knob_value)
    elif knob_type in ["2d_vector", "3d_vector", "color", "box"]:
        knob_value = [float(val_) for val_ in knob_value]

    return knob_value


def color_gui_to_int(color_gui):
    hex_value = (
        "0x{0:0>2x}{1:0>2x}{2:0>2x}{3:0>2x}").format(*color_gui)
    return int(hex_value, 16)


@deprecated
def add_rendering_knobs(node, farm=True):
    ''' Adds additional rendering knobs to given node

    Arguments:
        node (obj): nuke node object to be fixed

    Return:
        node (obj): with added knobs
    '''
    knob_options = ["Use existing frames", "Local"]
    if farm:
        knob_options.append("On farm")

    if "render" not in node.knobs():
        knob = nuke.Enumeration_Knob("render", "", knob_options)
        knob.clearFlag(nuke.STARTLINE)
        node.addKnob(knob)
    return node


@deprecated
def add_review_knob(node):
    ''' Adds additional review knob to given node

    Arguments:
        node (obj): nuke node object to be fixed

    Return:
        node (obj): with added knob
    '''
    if "review" not in node.knobs():
        knob = nuke.Boolean_Knob("review", "Review")
        knob.setValue(True)
        node.addKnob(knob)
    return node


@deprecated
def add_deadline_tab(node):
    # TODO: remove this as it is only linked to legacy create
    node.addKnob(nuke.Tab_Knob("Deadline"))

    knob = nuke.Int_Knob("deadlinePriority", "Priority")
    knob.setValue(50)
    node.addKnob(knob)

    knob = nuke.Int_Knob("deadlineChunkSize", "Chunk Size")
    knob.setValue(0)
    node.addKnob(knob)

    knob = nuke.Int_Knob("deadlineConcurrentTasks", "Concurrent tasks")
    # zero as default will get value from Settings during collection
    # instead of being an explicit user override, see precollect_write.py
    knob.setValue(0)
    node.addKnob(knob)

    knob = nuke.Text_Knob("divd", '')
    knob.setValue('')
    node.addKnob(knob)

    knob = nuke.Boolean_Knob("suspend_publish", "Suspend publish")
    knob.setValue(False)
    node.addKnob(knob)


@deprecated
def get_deadline_knob_names():
    # TODO: remove this as it is only linked to legacy
    # validate_write_deadline_tab
    return [
        "Deadline",
        "deadlineChunkSize",
        "deadlinePriority",
        "deadlineConcurrentTasks"
    ]


def create_backdrop(label="", color=None, layer=0,
                    nodes=None):
    """
    Create Backdrop node

    Arguments:
        color (str): nuke compatible string with color code
        layer (int): layer of node usually used (self.pos_layer - 1)
        label (str): the message
        nodes (list): list of nodes to be wrapped into backdrop

    """
    assert isinstance(nodes, list), "`nodes` should be a list of nodes"

    # Calculate bounds for the backdrop node.
    bdX = min([node.xpos() for node in nodes])
    bdY = min([node.ypos() for node in nodes])
    bdW = max([node.xpos() + node.screenWidth() for node in nodes]) - bdX
    bdH = max([node.ypos() + node.screenHeight() for node in nodes]) - bdY

    # Expand the bounds to leave a little border. Elements are offsets
    # for left, top, right and bottom edges respectively
    left, top, right, bottom = (-20, -65, 20, 60)
    bdX += left
    bdY += top
    bdW += (right - left)
    bdH += (bottom - top)

    bdn = nuke.createNode("BackdropNode")
    bdn["z_order"].setValue(layer)

    if color:
        bdn["tile_color"].setValue(int(color, 16))

    bdn["xpos"].setValue(bdX)
    bdn["ypos"].setValue(bdY)
    bdn["bdwidth"].setValue(bdW)
    bdn["bdheight"].setValue(bdH)

    if label:
        bdn["label"].setValue(label)

    bdn["note_font_size"].setValue(20)
    return bdn


class WorkfileSettings(object):
    """
    All settings for workfile will be set

    This object is setting all possible root settings to the workfile.
    Including Colorspace, Frame ranges, Resolution format. It can set it
    to Root node or to any given node.

    Arguments:
        root (node): nuke's root node
        nodes (list): list of nuke's nodes
        nodes_filter (list): filtering classes for nodes

    """

    def __init__(self, root_node=None, nodes=None, **kwargs):
        project_doc = kwargs.get("project")
        if project_doc is None:
            project_name = get_current_project_name()
            project_doc = get_project(project_name)
        else:
            project_name = project_doc["name"]

        Context._project_doc = project_doc
        self._project_name = project_name
        self._asset = (
            kwargs.get("asset_name")
            or get_current_asset_name()
        )
        self._asset_entity = get_asset_by_name(project_name, self._asset)
        self._root_node = root_node or nuke.root()
        self._nodes = self.get_nodes(nodes=nodes)

        self.data = kwargs

    def get_nodes(self, nodes=None, nodes_filter=None):

        if not isinstance(nodes, list) and not isinstance(nodes_filter, list):
            return [n for n in nuke.allNodes()]
        elif not isinstance(nodes, list) and isinstance(nodes_filter, list):
            nodes = list()
            for filter in nodes_filter:
                [nodes.append(n) for n in nuke.allNodes(filter=filter)]
            return nodes
        elif isinstance(nodes, list) and not isinstance(nodes_filter, list):
            return [n for n in self._nodes]
        elif isinstance(nodes, list) and isinstance(nodes_filter, list):
            for filter in nodes_filter:
                return [n for n in self._nodes if filter in n.Class()]

    def set_viewers_colorspace(self, viewer_dict):
        ''' Adds correct colorspace to viewer

        Arguments:
            viewer_dict (dict): adjustments from presets

        '''
        if not isinstance(viewer_dict, dict):
            msg = "set_viewers_colorspace(): argument should be dictionary"
            log.error(msg)
            nuke.message(msg)
            return

        filter_knobs = [
            "viewerProcess",
            "wipe_position"
        ]

        erased_viewers = []
        for v in nuke.allNodes(filter="Viewer"):
            # set viewProcess to preset from settings
            v["viewerProcess"].setValue(
                str(viewer_dict["viewerProcess"])
            )

            if str(viewer_dict["viewerProcess"]) \
                    not in v["viewerProcess"].value():
                copy_inputs = v.dependencies()
                copy_knobs = {k: v[k].value() for k in v.knobs()
                              if k not in filter_knobs}

                # delete viewer with wrong settings
                erased_viewers.append(v["name"].value())
                nuke.delete(v)

                # create new viewer
                nv = nuke.createNode("Viewer")

                # connect to original inputs
                for i, n in enumerate(copy_inputs):
                    nv.setInput(i, n)

                # set copied knobs
                for k, v in copy_knobs.items():
                    print(k, v)
                    nv[k].setValue(v)

                # set viewerProcess
                nv["viewerProcess"].setValue(str(viewer_dict["viewerProcess"]))

        if erased_viewers:
            log.warning(
                "Attention! Viewer nodes {} were erased."
                "It had wrong color profile".format(erased_viewers))

    def set_root_colorspace(self, imageio_host):
        ''' Adds correct colorspace to root

        Arguments:
            imageio_host (dict): host colorspace configurations

        '''
        config_data = get_imageio_config(
            project_name=get_current_project_name(),
            host_name="nuke"
        )

        workfile_settings = imageio_host["workfile"]
        viewer_process_settings = imageio_host["viewer"]["viewerProcess"]

        if not config_data:
            # TODO: backward compatibility for old projects - remove later
            # perhaps old project overrides is having it set to older version
            # with use of `customOCIOConfigPath`
            resolved_path = None
            if workfile_settings.get("customOCIOConfigPath"):
                unresolved_path = workfile_settings["customOCIOConfigPath"]
                ocio_paths = unresolved_path[platform.system().lower()]

                for ocio_p in ocio_paths:
                    resolved_path = str(ocio_p).format(**os.environ)
                    if not os.path.exists(resolved_path):
                        continue

            if resolved_path:
                # set values to root
                self._root_node["colorManagement"].setValue("OCIO")
                self._root_node["OCIO_config"].setValue("custom")
                self._root_node["customOCIOConfigPath"].setValue(
                    resolved_path)
            else:
                # no ocio config found and no custom path used
                if self._root_node["colorManagement"].value() \
                        not in str(workfile_settings["colorManagement"]):
                    self._root_node["colorManagement"].setValue(
                        str(workfile_settings["colorManagement"]))

                # second set ocio version
                if self._root_node["OCIO_config"].value() \
                        not in str(workfile_settings["OCIO_config"]):
                    self._root_node["OCIO_config"].setValue(
                        str(workfile_settings["OCIO_config"]))

        else:
            # OCIO config path is defined from prelaunch hook
            self._root_node["colorManagement"].setValue("OCIO")

            # print previous settings in case some were found in workfile
            residual_path = self._root_node["customOCIOConfigPath"].value()
            if residual_path:
                log.info("Residual OCIO config path found: `{}`".format(
                    residual_path
                ))

        # we dont need the key anymore
        workfile_settings.pop("customOCIOConfigPath", None)
        workfile_settings.pop("colorManagement", None)
        workfile_settings.pop("OCIO_config", None)

        # get monitor lut from settings respecting Nuke version differences
        monitor_lut = workfile_settings.pop("monitorLut", None)
        monitor_lut_data = self._get_monitor_settings(
            viewer_process_settings, monitor_lut)

        # set monitor related knobs luts (MonitorOut, Thumbnails)
        for knob, value_ in monitor_lut_data.items():
            workfile_settings[knob] = value_

        # then set the rest
        for knob, value_ in workfile_settings.items():
            # skip unfilled ocio config path
            # it will be dict in value
            if isinstance(value_, dict):
                continue
            # skip empty values
            if not value_:
                continue
            if self._root_node[knob].value() not in value_:
                self._root_node[knob].setValue(str(value_))
                log.debug("nuke.root()['{}'] changed to: {}".format(
                    knob, value_))

        # set ocio config path
        if config_data:
            config_path = config_data["path"].replace("\\", "/")
            log.info("OCIO config path found: `{}`".format(
                config_path))

            # check if there's a mismatch between environment and settings
            correct_settings = self._is_settings_matching_environment(
                config_data)

            # if there's no mismatch between environment and settings
            if correct_settings:
                self._set_ocio_config_path_to_workfile(config_data)

    def _get_monitor_settings(self, viewer_lut, monitor_lut):
        """ Get monitor settings from viewer and monitor lut

        Args:
            viewer_lut (str): viewer lut string
            monitor_lut (str): monitor lut string

        Returns:
            dict: monitor settings
        """
        output_data = {}
        m_display, m_viewer = get_viewer_config_from_string(monitor_lut)
        v_display, v_viewer = get_viewer_config_from_string(viewer_lut)

        # set monitor lut differently for nuke version 14
        if nuke.NUKE_VERSION_MAJOR >= 14:
            output_data["monitorOutLUT"] = create_viewer_profile_string(
                m_viewer, m_display, path_like=False)
            # monitorLut=thumbnails - viewerProcess makes more sense
            output_data["monitorLut"] = create_viewer_profile_string(
                v_viewer, v_display, path_like=False)

        if nuke.NUKE_VERSION_MAJOR == 13:
            output_data["monitorOutLUT"] = create_viewer_profile_string(
                m_viewer, m_display, path_like=False)
            # monitorLut=thumbnails - viewerProcess makes more sense
            output_data["monitorLut"] = create_viewer_profile_string(
                v_viewer, v_display, path_like=True)
        if nuke.NUKE_VERSION_MAJOR <= 12:
            output_data["monitorLut"] = create_viewer_profile_string(
                m_viewer, m_display, path_like=True)

        return output_data

    def _is_settings_matching_environment(self, config_data):
        """ Check if OCIO config path is different from environment

        Args:
            config_data (dict): OCIO config data from settings

        Returns:
            bool: True if settings are matching environment, False otherwise
        """
        current_ocio_path = os.environ["OCIO"]
        settings_ocio_path = config_data["path"]

        # normalize all paths to forward slashes
        current_ocio_path = current_ocio_path.replace("\\", "/")
        settings_ocio_path = settings_ocio_path.replace("\\", "/")

        if current_ocio_path != settings_ocio_path:
            message = """
It seems like there's a mismatch between the OCIO config path set in your Nuke
settings and the actual path set in your OCIO environment.

To resolve this, please follow these steps:
1. Close Nuke if it's currently open.
2. Reopen Nuke.

Please note the paths for your reference:

- The OCIO environment path currently set:
  `{env_path}`

- The path in your current Nuke settings:
  `{settings_path}`

Reopening Nuke should synchronize these paths and resolve any discrepancies.
"""
            nuke.message(
                message.format(
                    env_path=current_ocio_path,
                    settings_path=settings_ocio_path
                )
            )
            return False

        return True

    def _set_ocio_config_path_to_workfile(self, config_data):
        """ Set OCIO config path to workfile

        Path set into nuke workfile. It is trying to replace path with
        environment variable if possible. If not, it will set it as it is.
        It also saves the script to apply the change, but only if it's not
        empty Untitled script.

        Args:
            config_data (dict): OCIO config data from settings

        """
        # replace path with env var if possible
        ocio_path = self._replace_ocio_path_with_env_var(config_data)
        ocio_path = ocio_path.replace("\\", "/")

        log.info("Setting OCIO config path to: `{}`".format(
            ocio_path))

        self._root_node["customOCIOConfigPath"].setValue(
            ocio_path
        )
        self._root_node["OCIO_config"].setValue("custom")

        # only save script if it's not empty
        if self._root_node["name"].value() != "":
            log.info("Saving script to apply OCIO config path change.")
            nuke.scriptSave()

    def _get_included_vars(self, config_template):
        """ Get all environment variables included in template

        Args:
            config_template (str): OCIO config template from settings

        Returns:
            list: list of environment variables included in template
        """
        # resolve all environments for whitelist variables
        included_vars = [
            "BUILTIN_OCIO_ROOT",
        ]

        # include all project root related env vars
        for env_var in os.environ:
            if env_var.startswith("OPENPYPE_PROJECT_ROOT_"):
                included_vars.append(env_var)

        # use regex to find env var in template with format {ENV_VAR}
        # this way we make sure only template used env vars are included
        env_var_regex = r"\{([A-Z0-9_]+)\}"
        env_var = re.findall(env_var_regex, config_template)
        if env_var:
            included_vars.append(env_var[0])

        return included_vars

    def _replace_ocio_path_with_env_var(self, config_data):
        """ Replace OCIO config path with environment variable

        Environment variable is added as TCL expression to path. TCL expression
        is also replacing backward slashes found in path for windows
        formatted values.

        Args:
            config_data (str): OCIO config dict from settings

        Returns:
            str: OCIO config path with environment variable TCL expression
        """
        config_path = config_data["path"].replace("\\", "/")
        config_template = config_data["template"]

        included_vars = self._get_included_vars(config_template)

        # make sure we return original path if no env var is included
        new_path = config_path

        for env_var in included_vars:
            env_path = os.getenv(env_var)
            if not env_path:
                continue

            # it has to be directory current process can see
            if not os.path.isdir(env_path):
                continue

            # make sure paths are in same format
            env_path = env_path.replace("\\", "/")
            path = config_path.replace("\\", "/")

            # check if env_path is in path and replace to first found positive
            if env_path in path:
                # with regsub we make sure path format of slashes is correct
                resub_expr = (
                    "[regsub -all {{\\\\}} [getenv {}] \"/\"]").format(env_var)

                new_path = path.replace(
                    env_path, resub_expr
                )
                break

        return new_path

    def set_writes_colorspace(self):
        ''' Adds correct colorspace to write node dict

        '''
        for node in nuke.allNodes(filter="Group", group=self._root_node):
            log.info("Setting colorspace to `{}`".format(node.name()))

            # get data from avalon knob
            avalon_knob_data = read_avalon_data(node)
            node_data = get_node_data(node, INSTANCE_DATA_KNOB)

            if (
                # backward compatibility
                # TODO: remove this once old avalon data api will be removed
                avalon_knob_data
                and avalon_knob_data.get("id") != "pyblish.avalon.instance"
            ):
                continue
            elif (
                node_data
                and node_data.get("id") != "pyblish.avalon.instance"
            ):
                continue

            if (
                # backward compatibility
                # TODO: remove this once old avalon data api will be removed
                avalon_knob_data
                and "creator" not in avalon_knob_data
            ):
                continue
            elif (
                node_data
                and "creator_identifier" not in node_data
            ):
                continue

            nuke_imageio_writes = None
            if avalon_knob_data:
                # establish families
                families = [avalon_knob_data["family"]]
                if avalon_knob_data.get("families"):
                    families.append(avalon_knob_data.get("families"))

                nuke_imageio_writes = get_imageio_node_setting(
                    node_class=avalon_knob_data["families"],
                    plugin_name=avalon_knob_data["creator"],
                    subset=avalon_knob_data["subset"]
                )
            elif node_data:
                nuke_imageio_writes = get_write_node_template_attr(node)

            log.debug("nuke_imageio_writes: `{}`".format(nuke_imageio_writes))

            if not nuke_imageio_writes:
                return

            write_node = None

            # get into the group node
            node.begin()
            for x in nuke.allNodes():
                if x.Class() == "Write":
                    write_node = x
            node.end()

            if not write_node:
                return

            try:
                # write all knobs to node
                for knob in nuke_imageio_writes["knobs"]:
                    value = knob["value"]
                    if isinstance(value, six.text_type):
                        value = str(value)
                    if str(value).startswith("0x"):
                        value = int(value, 16)

                    log.debug("knob: {}| value: {}".format(
                        knob["name"], value
                    ))
                    write_node[knob["name"]].setValue(value)
            except TypeError:
                log.warning(
                    "Legacy workflow didn't work, switching to current")

                set_node_knobs_from_settings(
                    write_node, nuke_imageio_writes["knobs"])

    def set_reads_colorspace(self, read_clrs_inputs):
        """ Setting colorspace to Read nodes

        Looping through all read nodes and tries to set colorspace based
        on regex rules in presets
        """
        changes = {}
        for n in nuke.allNodes():
            file = nuke.filename(n)
            if n.Class() != "Read":
                continue

            # check if any colorspace presets for read is matching
            preset_clrsp = None

            for input in read_clrs_inputs:
                if not bool(re.search(input["regex"], file)):
                    continue
                preset_clrsp = input["colorspace"]

            if preset_clrsp is not None:
                current = n["colorspace"].value()
                future = str(preset_clrsp)
                if current != future:
                    changes[n.name()] = {
                        "from": current,
                        "to": future
                    }

        log.debug(changes)
        if changes:
            msg = "Read nodes are not set to correct colorspace:\n\n"
            for nname, knobs in changes.items():
                msg += (
                    " - node: '{0}' is now '{1}' but should be '{2}'\n"
                ).format(nname, knobs["from"], knobs["to"])

            msg += "\nWould you like to change it?"

            if nuke.ask(msg):
                for nname, knobs in changes.items():
                    n = nuke.toNode(nname)
                    n["colorspace"].setValue(knobs["to"])
                    log.info(
                        "Setting `{0}` to `{1}`".format(
                            nname,
                            knobs["to"]))

    def set_colorspace(self):
        ''' Setting colorspace following presets
        '''
        # get imageio
        nuke_colorspace = get_nuke_imageio_settings()

        log.info("Setting colorspace to workfile...")
        try:
            self.set_root_colorspace(nuke_colorspace)
        except AttributeError as _error:
            msg = "Set Colorspace to workfile error: {}".format(_error)
            nuke.message(msg)

        log.info("Setting colorspace to viewers...")
        try:
            self.set_viewers_colorspace(nuke_colorspace["viewer"])
        except AttributeError as _error:
            msg = "Set Colorspace to viewer error: {}".format(_error)
            nuke.message(msg)

        log.info("Setting colorspace to write nodes...")
        try:
            self.set_writes_colorspace()
        except AttributeError as _error:
            nuke.message(_error)
            log.error(_error)

        log.info("Setting colorspace to read nodes...")
        read_clrs_inputs = nuke_colorspace["regexInputs"].get("inputs", [])
        if read_clrs_inputs:
            self.set_reads_colorspace(read_clrs_inputs)

    def reset_frame_range_handles(self):
        """Set frame range to current asset"""

        if "data" not in self._asset_entity:
            msg = "Asset {} don't have set any 'data'".format(self._asset)
            log.warning(msg)
            nuke.message(msg)
            return

        asset_data = self._asset_entity["data"]

        missing_cols = []
        check_cols = ["fps", "frameStart", "frameEnd",
                      "handleStart", "handleEnd"]

        for col in check_cols:
            if col not in asset_data:
                missing_cols.append(col)

        if len(missing_cols) > 0:
            missing = ", ".join(missing_cols)
            msg = "'{}' are not set for asset '{}'!".format(
                missing, self._asset)
            log.warning(msg)
            nuke.message(msg)
            return

        # get handles values
        handle_start = asset_data["handleStart"]
        handle_end = asset_data["handleEnd"]

        fps = float(asset_data["fps"])
        frame_start_handle = int(asset_data["frameStart"]) - handle_start
        frame_end_handle = int(asset_data["frameEnd"]) + handle_end

        self._root_node["lock_range"].setValue(False)
        self._root_node["fps"].setValue(fps)
        self._root_node["first_frame"].setValue(frame_start_handle)
        self._root_node["last_frame"].setValue(frame_end_handle)
        self._root_node["lock_range"].setValue(True)

        # update node graph so knobs are updated
        update_node_graph()

        frame_range = '{0}-{1}'.format(
            int(asset_data["frameStart"]),
            int(asset_data["frameEnd"])
        )

        for node in nuke.allNodes(filter="Viewer"):
            node['frame_range'].setValue(frame_range)
            node['frame_range_lock'].setValue(True)
            node['frame_range'].setValue(frame_range)
            node['frame_range_lock'].setValue(True)

        if not ASSIST:
            set_node_data(
                self._root_node,
                INSTANCE_DATA_KNOB,
                {
                    "handleStart": int(handle_start),
                    "handleEnd": int(handle_end)
                }
            )
        else:
            log.warning(
                "NukeAssist mode is not allowing "
                "updating custom knobs..."
            )

    def reset_resolution(self):
        """Set resolution to project resolution."""
        log.info("Resetting resolution")
        project_name = get_current_project_name()
        asset_data = self._asset_entity["data"]

        format_data = {
            "width": int(asset_data.get(
                'resolutionWidth',
                asset_data.get('resolution_width'))),
            "height": int(asset_data.get(
                'resolutionHeight',
                asset_data.get('resolution_height'))),
            "pixel_aspect": asset_data.get(
                'pixelAspect',
                asset_data.get('pixel_aspect', 1)),
            "name": project_name
        }

        if any(x_ for x_ in format_data.values() if x_ is None):
            msg = ("Missing set shot attributes in DB."
                   "\nContact your supervisor!."
                   "\n\nWidth: `{width}`"
                   "\nHeight: `{height}`"
                   "\nPixel Aspect: `{pixel_aspect}`").format(**format_data)
            log.error(msg)
            nuke.message(msg)

        existing_format = None
        for format in nuke.formats():
            if format_data["name"] == format.name():
                existing_format = format
                break

        if existing_format:
            # Enforce existing format to be correct.
            existing_format.setWidth(format_data["width"])
            existing_format.setHeight(format_data["height"])
            existing_format.setPixelAspect(format_data["pixel_aspect"])
        else:
            format_string = self.make_format_string(**format_data)
            log.info("Creating new format: {}".format(format_string))
            nuke.addFormat(format_string)

        nuke.root()["format"].setValue(format_data["name"])
        log.info("Format is set.")

        # update node graph so knobs are updated
        update_node_graph()

    def make_format_string(self, **kwargs):
        if kwargs.get("r"):
            return (
                "{width} "
                "{height} "
                "{x} "
                "{y} "
                "{r} "
                "{t} "
                "{pixel_aspect:.2f} "
                "{name}".format(**kwargs)
            )
        else:
            return (
                "{width} "
                "{height} "
                "{pixel_aspect:.2f} "
                "{name}".format(**kwargs)
            )

    def set_context_settings(self):
        # replace reset resolution from avalon core to pype's
        self.reset_resolution()
        # replace reset resolution from avalon core to pype's
        self.reset_frame_range_handles()
        # add colorspace menu item
        self.set_colorspace()

    def set_favorites(self):
        from .utils import set_context_favorites

        work_dir = os.getenv("AVALON_WORKDIR")
        asset = get_current_asset_name()
        favorite_items = OrderedDict()

        # project
        # get project's root and split to parts
        projects_root = os.path.normpath(work_dir.split(
            Context.project_name)[0])
        # add project name
        project_dir = os.path.join(projects_root, Context.project_name) + "/"
        # add to favorites
        favorite_items.update({"Project dir": project_dir.replace("\\", "/")})

        # asset
        asset_root = os.path.normpath(work_dir.split(
            asset)[0])
        # add asset name
        asset_dir = os.path.join(asset_root, asset) + "/"
        # add to favorites
        favorite_items.update({"Shot dir": asset_dir.replace("\\", "/")})

        # workdir
        favorite_items.update({"Work dir": work_dir.replace("\\", "/")})

        set_context_favorites(favorite_items)


def get_write_node_template_attr(node):
    ''' Gets all defined data from presets

    '''

    # TODO: add identifiers to settings and rename settings key
    plugin_names_mapping = {
        "create_write_image": "CreateWriteImage",
        "create_write_prerender": "CreateWritePrerender",
        "create_write_render": "CreateWriteRender"
    }
    # get avalon data from node
    node_data = get_node_data(node, INSTANCE_DATA_KNOB)
    identifier = node_data["creator_identifier"]

    # return template data
    return get_imageio_node_setting(
        node_class="Write",
        plugin_name=plugin_names_mapping[identifier],
        subset=node_data["subset"]
    )


def get_dependent_nodes(nodes):
    """Get all dependent nodes connected to the list of nodes.

    Looking for connections outside of the nodes in incoming argument.

    Arguments:
        nodes (list): list of nuke.Node objects

    Returns:
        connections_in: dictionary of nodes and its dependencies
        connections_out: dictionary of nodes and its dependency
    """

    connections_in = dict()
    connections_out = dict()
    node_names = [n.name() for n in nodes]
    for node in nodes:
        inputs = node.dependencies()
        outputs = node.dependent()
        # collect all inputs outside
        test_in = [(i, n) for i, n in enumerate(inputs)
                   if n.name() not in node_names]
        if test_in:
            connections_in.update({
                node: test_in
            })
        # collect all outputs outside
        test_out = [i for i in outputs if i.name() not in node_names]
        if test_out:
            # only one dependent node is allowed
            connections_out.update({
                node: test_out[-1]
            })

    return connections_in, connections_out


def update_node_graph():
    # Resetting frame will update knob values
    try:
        root_node_lock = nuke.root()["lock_range"].value()
        nuke.root()["lock_range"].setValue(not root_node_lock)
        nuke.root()["lock_range"].setValue(root_node_lock)

        current_frame = nuke.frame()
        nuke.frame(1)
        nuke.frame(int(current_frame))
    except Exception as error:
        log.warning(error)


def find_free_space_to_paste_nodes(
    nodes,
    group=nuke.root(),
    direction="right",
    offset=300
):
    """
    For getting coordinates in DAG (node graph) for placing new nodes

    Arguments:
        nodes (list): list of nuke.Node objects
        group (nuke.Node) [optional]: object in which context it is
        direction (str) [optional]: where we want it to be placed
                                    [left, right, top, bottom]
        offset (int) [optional]: what offset it is from rest of nodes

    Returns:
        xpos (int): x coordinace in DAG
        ypos (int): y coordinace in DAG
    """
    if len(nodes) == 0:
        return 0, 0

    group_xpos = list()
    group_ypos = list()

    # get local coordinates of all nodes
    nodes_xpos = [n.xpos() for n in nodes] + \
                 [n.xpos() + n.screenWidth() for n in nodes]

    nodes_ypos = [n.ypos() for n in nodes] + \
                 [n.ypos() + n.screenHeight() for n in nodes]

    # get complete screen size of all nodes to be placed in
    nodes_screen_width = max(nodes_xpos) - min(nodes_xpos)
    nodes_screen_heigth = max(nodes_ypos) - min(nodes_ypos)

    # get screen size (r,l,t,b) of all nodes in `group`
    with group:
        group_xpos = [n.xpos() for n in nuke.allNodes() if n not in nodes] + \
                     [n.xpos() + n.screenWidth() for n in nuke.allNodes()
                      if n not in nodes]
        group_ypos = [n.ypos() for n in nuke.allNodes() if n not in nodes] + \
                     [n.ypos() + n.screenHeight() for n in nuke.allNodes()
                      if n not in nodes]

        # calc output left
        if direction in "left":
            xpos = min(group_xpos) - abs(nodes_screen_width) - abs(offset)
            ypos = min(group_ypos)
            return xpos, ypos
        # calc output right
        if direction in "right":
            xpos = max(group_xpos) + abs(offset)
            ypos = min(group_ypos)
            return xpos, ypos
        # calc output top
        if direction in "top":
            xpos = min(group_xpos)
            ypos = min(group_ypos) - abs(nodes_screen_heigth) - abs(offset)
            return xpos, ypos
        # calc output bottom
        if direction in "bottom":
            xpos = min(group_xpos)
            ypos = max(group_ypos) + abs(offset)
            return xpos, ypos


@contextlib.contextmanager
def maintained_selection():
    """Maintain selection during context

    Example:
        >>> with maintained_selection():
        ...     node["selected"].setValue(True)
        >>> print(node["selected"].value())
        False
    """
    previous_selection = nuke.selectedNodes()
    try:
        yield
    finally:
        # unselect all selection in case there is some
        reset_selection()

        # and select all previously selected nodes
        if previous_selection:
            select_nodes(previous_selection)


def reset_selection():
    """Deselect all selected nodes"""
    for node in nuke.selectedNodes():
        node["selected"].setValue(False)


def select_nodes(nodes):
    """Selects all inputted nodes

    Arguments:
        nodes (list): nuke nodes to be selected
    """
    assert isinstance(nodes, (list, tuple)), "nodes has to be list or tuple"

    for node in nodes:
        node["selected"].setValue(True)


def launch_workfiles_app():
    """Show workfiles tool on nuke launch.

    Trigger to show workfiles tool on application launch. Can be executed only
    once all other calls are ignored.

    Workfiles tool show is deferred after application initialization using
    QTimer.
    """

    if Context.workfiles_launched:
        return

    Context.workfiles_launched = True

    # get all imortant settings
    open_at_start = env_value_to_bool(
        env_key="OPENPYPE_WORKFILE_TOOL_ON_START",
        default=None)

    # return if none is defined
    if not open_at_start:
        return

    # Show workfiles tool using timer
    # - this will be probably triggered during initialization in that case
    #   the application is not be able to show uis so it must be
    #   deferred using timer
    # - timer should be processed when initialization ends
    #       When applications starts to process events.
    timer = QtCore.QTimer()
    timer.timeout.connect(_launch_workfile_app)
    timer.setInterval(100)
    Context.workfiles_tool_timer = timer
    timer.start()


def _launch_workfile_app():
    # Safeguard to not show window when application is still starting up
    #   or is already closing down.
    closing_down = QtWidgets.QApplication.closingDown()
    starting_up = QtWidgets.QApplication.startingUp()

    # Stop the timer if application finished start up of is closing down
    if closing_down or not starting_up:
        Context.workfiles_tool_timer.stop()
        Context.workfiles_tool_timer = None

    # Skip if application is starting up or closing down
    if starting_up or closing_down:
        return

    # Make sure on top is enabled on first show so the window is not hidden
    #   under main nuke window
    #   - this happened on Centos 7 and it is because the focus of nuke
    #       changes to the main window after showing because of initialization
    #       which moves workfiles tool under it
    host_tools.show_workfiles(parent=None, on_top=True)


@deprecated("openpype.hosts.nuke.api.lib.start_workfile_template_builder")
def process_workfile_builder():
    """ [DEPRECATED] Process workfile builder on nuke start

    This function is deprecated and will be removed in future versions.
    Use settings for `project_settings/nuke/templated_workfile_build` which are
    supported by api `start_workfile_template_builder()`.
    """

    # to avoid looping of the callback, remove it!
    nuke.removeOnCreate(process_workfile_builder, nodeClass="Root")

    # get state from settings
    project_settings = get_current_project_settings()
    workfile_builder = project_settings["nuke"].get(
        "workfile_builder", {})

    # get settings
    createfv_on = workfile_builder.get("create_first_version") or None
    builder_on = workfile_builder.get("builder_on_start") or None

    last_workfile_path = os.environ.get("AVALON_LAST_WORKFILE")

    # generate first version in file not existing and feature is enabled
    if createfv_on and not os.path.exists(last_workfile_path):
        # get custom template path if any
        custom_template_path = get_custom_workfile_template_from_session(
            project_settings=project_settings
        )

        # if custom template is defined
        if custom_template_path:
            log.info("Adding nodes from `{}`...".format(
                custom_template_path
            ))
            try:
                # import nodes into current script
                nuke.nodePaste(custom_template_path)
            except RuntimeError:
                raise RuntimeError((
                    "Template defined for project: {} is not working. "
                    "Talk to your manager for an advise").format(
                        custom_template_path))

        # if builder at start is defined
        if builder_on:
            log.info("Building nodes from presets...")
            # build nodes by defined presets
            BuildWorkfile().process()

        log.info("Saving script as version `{}`...".format(
            last_workfile_path
        ))
        # safe file as version
        save_file(last_workfile_path)
        return


def start_workfile_template_builder():
    from .workfile_template_builder import (
        build_workfile_template
    )

    # remove callback since it would be duplicating the workfile
    nuke.removeOnCreate(start_workfile_template_builder, nodeClass="Root")

    # to avoid looping of the callback, remove it!
    log.info("Starting workfile template builder...")
    try:
        build_workfile_template(workfile_creation_enabled=True)
    except TemplateProfileNotFound:
        log.warning("Template profile not found. Skipping...")


@deprecated
def recreate_instance(origin_node, avalon_data=None):
    """Recreate input instance to different data

    Args:
        origin_node (nuke.Node): Nuke node to be recreating from
        avalon_data (dict, optional): data to be used in new node avalon_data

    Returns:
        nuke.Node: newly created node
    """
    knobs_wl = ["render", "publish", "review", "ypos",
                "use_limit", "first", "last"]
    # get data from avalon knobs
    data = get_avalon_knob_data(
        origin_node)

    # add input data to avalon data
    if avalon_data:
        data.update(avalon_data)

    # capture all node knobs allowed in op_knobs
    knobs_data = {k: origin_node[k].value()
                  for k in origin_node.knobs()
                  for key in knobs_wl
                  if key in k}

    # get node dependencies
    inputs = origin_node.dependencies()
    outputs = origin_node.dependent()

    # remove the node
    nuke.delete(origin_node)

    # create new node
    # get appropriate plugin class
    creator_plugin = None
    for Creator in discover_legacy_creator_plugins():
        if Creator.__name__ == data["creator"]:
            creator_plugin = Creator
            break

    # create write node with creator
    new_node_name = data["subset"]
    new_node = creator_plugin(new_node_name, data["asset"]).process()

    # white listed knobs to the new node
    for _k, _v in knobs_data.items():
        try:
            print(_k, _v)
            new_node[_k].setValue(_v)
        except Exception as e:
            print(e)

    # connect to original inputs
    for i, n in enumerate(inputs):
        new_node.setInput(i, n)

    # connect to outputs
    if len(outputs) > 0:
        for dn in outputs:
            dn.setInput(0, new_node)

    return new_node


def add_scripts_menu():
    try:
        from scriptsmenu import launchfornuke
    except ImportError:
        log.warning(
            "Skipping studio.menu install, because "
            "'scriptsmenu' module seems unavailable."
        )
        return

    # load configuration of custom menu
    project_name = get_current_project_name()
    project_settings = get_project_settings(project_name)
    config = project_settings["nuke"]["scriptsmenu"]["definition"]
    _menu = project_settings["nuke"]["scriptsmenu"]["name"]

    if not config:
        log.warning("Skipping studio menu, no definition found.")
        return

    # run the launcher for Maya menu
    studio_menu = launchfornuke.main(title=_menu.title())

    # apply configuration
    studio_menu.build_from_configuration(studio_menu, config)


def add_scripts_gizmo():

    # load configuration of custom menu
    project_name = get_current_project_name()
    project_settings = get_project_settings(project_name)
    platform_name = platform.system().lower()

    for gizmo_settings in project_settings["nuke"]["gizmo"]:
        gizmo_list_definition = gizmo_settings["gizmo_definition"]
        toolbar_name = gizmo_settings["toolbar_menu_name"]
        # gizmo_toolbar_path = gizmo_settings["gizmo_toolbar_path"]
        gizmo_source_dir = gizmo_settings.get(
            "gizmo_source_dir", {}).get(platform_name)
        toolbar_icon_path = gizmo_settings.get(
            "toolbar_icon_path", {}).get(platform_name)

        if not gizmo_source_dir:
            log.debug("Skipping studio gizmo `{}`, "
                      "no gizmo path found.".format(toolbar_name)
                      )
            return

        if not gizmo_list_definition:
            log.debug("Skipping studio gizmo `{}`, "
                      "no definition found.".format(toolbar_name)
                      )
            return

        if toolbar_icon_path:
            try:
                toolbar_icon_path = toolbar_icon_path.format(**os.environ)
            except KeyError as e:
                log.error(
                    "This environment variable doesn't exist: {}".format(e)
                )

        existing_gizmo_path = []
        for source_dir in gizmo_source_dir:
            try:
                resolve_source_dir = source_dir.format(**os.environ)
            except KeyError as e:
                log.error(
                    "This environment variable doesn't exist: {}".format(e)
                )
                continue
            if not os.path.exists(resolve_source_dir):
                log.warning(
                    "The source of gizmo `{}` does not exists".format(
                        resolve_source_dir
                    )
                )
                continue
            existing_gizmo_path.append(resolve_source_dir)

        # run the launcher for Nuke toolbar
        toolbar_menu = gizmo_menu.GizmoMenu(
            title=toolbar_name,
            icon=toolbar_icon_path
        )

        # apply configuration
        toolbar_menu.add_gizmo_path(existing_gizmo_path)
        toolbar_menu.build_from_configuration(gizmo_list_definition)


class NukeDirmap(HostDirmap):
    def __init__(self, file_name, *args, **kwargs):
        """
        Args:
            file_name (str): full path of referenced file from workfiles
            *args (tuple): Positional arguments for 'HostDirmap' class
            **kwargs (dict): Keyword arguments for 'HostDirmap' class
        """

        self.file_name = file_name
        super(NukeDirmap, self).__init__(*args, **kwargs)

    def on_enable_dirmap(self):
        pass

    def dirmap_routine(self, source_path, destination_path):
        source_path = source_path.lower().replace(os.sep, '/')
        destination_path = destination_path.lower().replace(os.sep, '/')
        log.debug("Map: {} with: {}->{}".format(self.file_name,
                                                source_path, destination_path))
        if platform.system().lower() == "windows":
            self.file_name = self.file_name.lower().replace(
                source_path, destination_path)
        else:
            self.file_name = self.file_name.replace(
                source_path, destination_path)


class DirmapCache:
    """Caching class to get settings and sync_module easily and only once."""
    _project_name = None
    _project_settings = None
    _sync_module_discovered = False
    _sync_module = None
    _mapping = None

    @classmethod
    def project_name(cls):
        if cls._project_name is None:
            cls._project_name = os.getenv("AVALON_PROJECT")
        return cls._project_name

    @classmethod
    def project_settings(cls):
        if cls._project_settings is None:
            cls._project_settings = get_project_settings(cls.project_name())
        return cls._project_settings

    @classmethod
    def sync_module(cls):
        if not cls._sync_module_discovered:
            cls._sync_module_discovered = True
            cls._sync_module = ModulesManager().modules_by_name.get(
                "sync_server")
        return cls._sync_module

    @classmethod
    def mapping(cls):
        return cls._mapping

    @classmethod
    def set_mapping(cls, mapping):
        cls._mapping = mapping


def dirmap_file_name_filter(file_name):
    """Nuke callback function with single full path argument.

        Checks project settings for potential mapping from source to dest.
    """

    dirmap_processor = NukeDirmap(
        file_name,
        "nuke",
        DirmapCache.project_name(),
        DirmapCache.project_settings(),
        DirmapCache.sync_module(),
    )
    if not DirmapCache.mapping():
        DirmapCache.set_mapping(dirmap_processor.get_mappings())

    dirmap_processor.process_dirmap(DirmapCache.mapping())
    if os.path.exists(dirmap_processor.file_name):
        return dirmap_processor.file_name
    return file_name


@contextlib.contextmanager
def node_tempfile():
    """Create a temp file where node is pasted during duplication.

    This is to avoid using clipboard for node duplication.
    """

    tmp_file = tempfile.NamedTemporaryFile(
        mode="w", prefix="openpype_nuke_temp_", suffix=".nk", delete=False
    )
    tmp_file.close()
    node_tempfile_path = tmp_file.name

    try:
        # Yield the path where node can be copied
        yield node_tempfile_path

    finally:
        # Remove the file at the end
        os.remove(node_tempfile_path)


def duplicate_node(node):
    reset_selection()

    # select required node for duplication
    node.setSelected(True)

    with node_tempfile() as filepath:
        # copy selected to temp filepath
        nuke.nodeCopy(filepath)

        # reset selection
        reset_selection()

        # paste node and selection is on it only
        dupli_node = nuke.nodePaste(filepath)

    # reset selection
    reset_selection()

    return dupli_node


def get_group_io_nodes(nodes):
    """Get the input and the output of a group of nodes."""

    if not nodes:
        raise ValueError("there is no nodes in the list")

    input_node = None
    output_node = None

    if len(nodes) == 1:
        input_node = output_node = nodes[0]

    else:
        for node in nodes:
            if "Input" in node.name():
                input_node = node

            if "Output" in node.name():
                output_node = node

            if input_node is not None and output_node is not None:
                break

        if input_node is None:
            log.warning("No Input found")

        if output_node is None:
            log.warning("No Output found")

    return input_node, output_node


def get_extreme_positions(nodes):
    """Get the 4 numbers that represent the box of a group of nodes."""

    if not nodes:
        raise ValueError("there is no nodes in the list")

    nodes_xpos = [n.xpos() for n in nodes] + \
        [n.xpos() + n.screenWidth() for n in nodes]

    nodes_ypos = [n.ypos() for n in nodes] + \
        [n.ypos() + n.screenHeight() for n in nodes]

    min_x, min_y = (min(nodes_xpos), min(nodes_ypos))
    max_x, max_y = (max(nodes_xpos), max(nodes_ypos))
    return min_x, min_y, max_x, max_y


def refresh_node(node):
    """Correct a bug caused by the multi-threading of nuke.

    Refresh the node to make sure that it takes the desired attributes.
    """

    x = node.xpos()
    y = node.ypos()
    nuke.autoplaceSnap(node)
    node.setXYpos(x, y)


def refresh_nodes(nodes):
    for node in nodes:
        refresh_node(node)


def get_names_from_nodes(nodes):
    """Get list of nodes names.

    Args:
        nodes(List[nuke.Node]): List of nodes to convert into names.

    Returns:
        List[str]: Name of passed nodes.
    """

    return [
        node.name()
        for node in nodes
    ]


def get_nodes_by_names(names):
    """Get list of nuke nodes based on their names.

    Args:
        names (List[str]): List of node names to be found.

    Returns:
        List[nuke.Node]: List of nodes found by name.
    """

    return [
        nuke.toNode(name)
        for name in names
    ]


def get_viewer_config_from_string(input_string):
    """Convert string to display and viewer string

    Args:
        input_string (str): string with viewer

    Raises:
        IndexError: if more then one slash in input string
        IndexError: if missing closing bracket

    Returns:
        tuple[str]: display, viewer
    """
    display = None
    viewer = input_string
    # check if () or / or \ in name
    if "/" in viewer:
        split = viewer.split("/")

        # rise if more then one column
        if len(split) > 2:
            raise IndexError((
                "Viewer Input string is not correct. "
                "more then two `/` slashes! {}"
            ).format(input_string))

        viewer = split[1]
        display = split[0]
    elif "(" in viewer:
        pattern = r"([\w\d\s\.\-]+).*[(](.*)[)]"
        result_ = re.findall(pattern, viewer)
        try:
            result_ = result_.pop()
            display = str(result_[1]).rstrip()
            viewer = str(result_[0]).rstrip()
        except IndexError:
            raise IndexError((
                "Viewer Input string is not correct. "
                "Missing bracket! {}"
            ).format(input_string))

    return (display, viewer)


def create_viewer_profile_string(viewer, display=None, path_like=False):
    """Convert viewer and display to string

    Args:
        viewer (str): viewer name
        display (Optional[str]): display name
        path_like (Optional[bool]): if True, return path like string

    Returns:
        str: viewer config string
    """
    if not display:
        return viewer

    if path_like:
        return "{}/{}".format(display, viewer)
    return "{} ({})".format(viewer, display)


def get_filenames_without_hash(filename, frame_start, frame_end):
    """Get filenames without frame hash
        i.e. "renderCompositingMain.baking.0001.exr"

    Args:
        filename (str): filename with frame hash
        frame_start (str): start of the frame
        frame_end (str): end of the frame

    Returns:
        list: filename per frame of the sequence
    """
    filenames = []
    for frame in range(int(frame_start), (int(frame_end) + 1)):
        if "#" in filename:
            # use regex to convert #### to {:0>4}
            def replace(match):
                return "{{:0>{}}}".format(len(match.group()))
            filename_without_hashes = re.sub("#+", replace, filename)
            new_filename = filename_without_hashes.format(frame)
            filenames.append(new_filename)
    return filenames
