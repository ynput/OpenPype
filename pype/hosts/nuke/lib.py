import os
import re
import sys
from collections import OrderedDict

from avalon import api, io, lib
import avalon.nuke
from avalon.nuke import lib as anlib
import pype.api as pype

import nuke


from .presets import (
    get_colorspace_preset,
    get_node_dataflow_preset,
    get_node_colorspace_preset,
    get_anatomy
)

from .utils import set_context_favorites

log = pype.Logger().get_logger(__name__, "nuke")

self = sys.modules[__name__]
self._project = None


def on_script_load():
    ''' Callback for ffmpeg support
    '''
    if nuke.env['LINUX']:
        nuke.tcl('load ffmpegReader')
        nuke.tcl('load ffmpegWriter')
    else:
        nuke.tcl('load movReader')
        nuke.tcl('load movWriter')


def check_inventory_versions():
    """
    Actiual version idetifier of Loaded containers

    Any time this function is run it will check all nodes and filter only
    Loader nodes for its version. It will get all versions from database
    and check if the node is having actual version. If not then it will color
    it to red.
    """
    # get all Loader nodes by avalon attribute metadata
    for each in nuke.allNodes():
        if each.Class() == 'Read':
            container = avalon.nuke.parse_container(each)

            if container:
                node = container["_node"]
                avalon_knob_data = avalon.nuke.get_avalon_knob_data(
                    node, ['avalon:', 'ak:'])

                # get representation from io
                representation = io.find_one({
                    "type": "representation",
                    "_id": io.ObjectId(avalon_knob_data["representation"])
                })

                # Get start frame from version data
                version = io.find_one({
                    "type": "version",
                    "_id": representation["parent"]
                })

                # get all versions in list
                versions = io.find({
                    "type": "version",
                    "parent": version["parent"]
                }).distinct('name')

                max_version = max(versions)

                # check the available version and do match
                # change color of node if not max verion
                if version.get("name") not in [max_version]:
                    node["tile_color"].setValue(int("0xd84f20ff", 16))
                else:
                    node["tile_color"].setValue(int("0x4ecd25ff", 16))


def writes_version_sync():
    ''' Callback synchronizing version of publishable write nodes
    '''
    try:
        rootVersion = pype.get_version_from_path(nuke.root().name())
        padding = len(rootVersion)
        new_version = "v" + str("{" + ":0>{}".format(padding) + "}").format(
            int(rootVersion)
        )
        log.debug("new_version: {}".format(new_version))
    except Exception:
        return

    for each in nuke.allNodes():
        if each.Class() == 'Write':
            # check if the node is avalon tracked
            if "AvalonTab" not in each.knobs():
                continue

            avalon_knob_data = avalon.nuke.get_avalon_knob_data(
                each, ['avalon:', 'ak:'])

            try:
                if avalon_knob_data['families'] not in ["render"]:
                    log.debug(avalon_knob_data['families'])
                    continue

                node_file = each['file'].value()

                node_version = "v" + pype.get_version_from_path(node_file)
                log.debug("node_version: {}".format(node_version))

                node_new_file = node_file.replace(node_version, new_version)
                each['file'].setValue(node_new_file)
                if not os.path.isdir(os.path.dirname(node_new_file)):
                    log.warning("Path does not exist! I am creating it.")
                    os.makedirs(os.path.dirname(node_new_file), 0o766)
            except Exception as e:
                log.warning(
                    "Write node: `{}` has no version in path: {}".format(
                        each.name(), e))


def version_up_script():
    ''' Raising working script's version
    '''
    import nukescripts
    nukescripts.script_and_write_nodes_version_up()


def get_render_path(node):
    ''' Generate Render path from presets regarding avalon knob data
    '''
    data = dict()
    data['avalon'] = avalon.nuke.get_avalon_knob_data(
        node, ['avalon:', 'ak:'])

    data_preset = {
        "class": data['avalon']['family'],
        "preset": data['avalon']['families']
    }

    nuke_dataflow_writes = get_node_dataflow_preset(**data_preset)
    nuke_colorspace_writes = get_node_colorspace_preset(**data_preset)

    application = lib.get_application(os.environ["AVALON_APP_NAME"])
    data.update({
        "application": application,
        "nuke_dataflow_writes": nuke_dataflow_writes,
        "nuke_colorspace_writes": nuke_colorspace_writes
    })

    anatomy_filled = format_anatomy(data)
    return anatomy_filled["render"]["path"].replace("\\", "/")


def format_anatomy(data):
    ''' Helping function for formating of anatomy paths

    Arguments:
        data (dict): dictionary with attributes used for formating

    Return:
        path (str)
    '''
    # TODO: perhaps should be nonPublic

    anatomy = get_anatomy()
    log.debug("__ anatomy.templates: {}".format(anatomy.templates))

    try:
        # TODO: bck compatibility with old anatomy template
        padding = int(
            anatomy.templates["render"].get(
                "frame_padding",
                anatomy.templates["render"].get("padding")
            )
        )
    except KeyError as e:
        msg = ("`padding` key is not in `render` "
               "or `frame_padding` on is not available in "
               "Anatomy template. Please, add it there and restart "
               "the pipeline (padding: \"4\"): `{}`").format(e)

        log.error(msg)
        nuke.message(msg)

    version = data.get("version", None)
    if not version:
        file = script_name()
        data["version"] = pype.get_version_from_path(file)
    project_document = pype.get_project()
    data.update({
        "subset": data["avalon"]["subset"],
        "asset": data["avalon"]["asset"],
        "task": api.Session["AVALON_TASK"],
        "family": data["avalon"]["family"],
        "project": {"name": project_document["name"],
                    "code": project_document["data"].get("code", '')},
        "representation": data["nuke_dataflow_writes"]["file_type"],
        "app": data["application"]["application_dir"],
        "hierarchy": pype.get_hierarchy(),
        "frame": "#" * padding,
    })
    return anatomy.format(data)


def script_name():
    ''' Returns nuke script path
    '''
    return nuke.root().knob('name').value()


def add_button_write_to_read(node):
    name = "createReadNode"
    label = "[ Create Read ]"
    value = "import write_to_read;write_to_read.write_to_read(nuke.thisNode())"
    k = nuke.PyScript_Knob(name, label, value)
    k.setFlag(0x1000)
    node.addKnob(k)


def create_write_node(name, data, input=None, prenodes=None, review=True):
    ''' Creating write node which is group node

    Arguments:
        name (str): name of node
        data (dict): data to be imprinted
        input (node): selected node to connect to
        prenodes (list, optional): list of lists, definitions for nodes
                                to be created before write
        review (bool): adding review knob

    Example:
        prenodes = [(
            "NameNode",  # string
            "NodeClass",  # string
            (   # OrderDict: knob and values pairs
                ("knobName", "knobValue"),
                ("knobName", "knobValue")
            ),
            (   # list outputs
                "firstPostNodeName",
                "secondPostNodeName"
            )
        )
        ]

    Return:
        node (obj): group node with avalon data as Knobs
    '''

    nuke_dataflow_writes = get_node_dataflow_preset(**data)
    nuke_colorspace_writes = get_node_colorspace_preset(**data)
    application = lib.get_application(os.environ["AVALON_APP_NAME"])

    try:
        data.update({
            "application": application,
            "nuke_dataflow_writes": nuke_dataflow_writes,
            "nuke_colorspace_writes": nuke_colorspace_writes
        })
        anatomy_filled = format_anatomy(data)

    except Exception as e:
        msg = "problem with resolving anatomy tepmlate: {}".format(e)
        log.error(msg)
        nuke.message(msg)

    # build file path to workfiles
    fpath = str(anatomy_filled["work"]["folder"]).replace("\\", "/")
    fpath = data["fpath_template"].format(
        work=fpath, version=data["version"], subset=data["subset"],
        frame=data["frame"],
        ext=data["nuke_dataflow_writes"]["file_type"]
    )

    # create directory
    if not os.path.isdir(os.path.dirname(fpath)):
        log.warning("Path does not exist! I am creating it.")
        os.makedirs(os.path.dirname(fpath), 0o766)

    _data = OrderedDict({
        "file": fpath
    })

    # adding dataflow template
    log.debug("nuke_dataflow_writes: `{}`".format(nuke_dataflow_writes))
    {_data.update({k: v})
     for k, v in nuke_dataflow_writes.items()
     if k not in ["_id", "_previous"]}

    # adding colorspace template
    log.debug("nuke_colorspace_writes: `{}`".format(nuke_colorspace_writes))
    {_data.update({k: v})
     for k, v in nuke_colorspace_writes.items()}

    _data = avalon.nuke.lib.fix_data_for_node_create(_data)

    log.debug("_data: `{}`".format(_data))

    if "frame_range" in data.keys():
        _data["frame_range"] = data.get("frame_range", None)
        log.debug("_data[frame_range]: `{}`".format(_data["frame_range"]))

    GN = nuke.createNode("Group", "name {}".format(name))

    prev_node = None
    with GN:
        connections = list()
        if input:
            # if connected input node was defined
            connections.append({
                "node": input,
                "inputName": input.name()})
            prev_node = nuke.createNode(
                "Input", "name {}".format(input.name()))
        else:
            # generic input node connected to nothing
            prev_node = nuke.createNode(
                "Input", "name {}".format("rgba"))

        # creating pre-write nodes `prenodes`
        if prenodes:
            for name, klass, properties, set_output_to in prenodes:
                # create node
                now_node = nuke.createNode(klass, "name {}".format(name))

                # add data to knob
                for k, v in properties:
                    try:
                        now_node[k].value()
                    except NameError:
                        log.warning(
                            "knob `{}` does not exist on node `{}`".format(
                                k, now_node["name"].value()
                            ))
                        continue

                    if k and v:
                        now_node[k].setValue(str(v))

                # connect to previous node
                if set_output_to:
                    if isinstance(set_output_to, (tuple or list)):
                        for i, node_name in enumerate(set_output_to):
                            input_node = nuke.createNode(
                                "Input", "name {}".format(node_name))
                            connections.append({
                                "node": nuke.toNode(node_name),
                                "inputName": node_name})
                            now_node.setInput(1, input_node)
                    elif isinstance(set_output_to, str):
                        input_node = nuke.createNode(
                            "Input", "name {}".format(node_name))
                        connections.append({
                            "node": nuke.toNode(set_output_to),
                            "inputName": set_output_to})
                        now_node.setInput(0, input_node)
                else:
                    now_node.setInput(0, prev_node)

                # swith actual node to previous
                prev_node = now_node

        # creating write node
        write_node = now_node = avalon.nuke.lib.add_write_node(
            "inside_{}".format(name),
            **_data
        )

        # connect to previous node
        now_node.setInput(0, prev_node)

        # swith actual node to previous
        prev_node = now_node

        now_node = nuke.createNode("Output", "name Output1")

        # connect to previous node
        now_node.setInput(0, prev_node)

    # imprinting group node
    avalon.nuke.imprint(GN, data["avalon"])

    divider = nuke.Text_Knob('')
    GN.addKnob(divider)

    add_rendering_knobs(GN)

    if review:
        add_review_knob(GN)

    # Add linked knobs.
    linked_knob_names = ["Render", "use_limit", "first", "last"]
    for name in linked_knob_names:
        link = nuke.Link_Knob(name)
        link.makeLink(write_node.name(), name)
        link.setName(name)
        GN.addKnob(link)

    divider = nuke.Text_Knob('')
    GN.addKnob(divider)

    # adding write to read button
    add_button_write_to_read(GN)

    # Deadline tab.
    add_deadline_tab(GN)

    # set tile color
    tile_color = _data.get("tile_color", "0xff0000ff")
    GN["tile_color"].setValue(tile_color)

    return GN


def add_rendering_knobs(node):
    ''' Adds additional rendering knobs to given node

    Arguments:
        node (obj): nuke node object to be fixed

    Return:
        node (obj): with added knobs
    '''
    if "render" not in node.knobs():
        knob = nuke.Boolean_Knob("render", "Render")
        knob.setFlag(0x1000)
        knob.setValue(False)
        node.addKnob(knob)
    if "render_farm" not in node.knobs():
        knob = nuke.Boolean_Knob("render_farm", "Render on Farm")
        knob.setValue(False)
        node.addKnob(knob)
    return node


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


def add_deadline_tab(node):
    node.addKnob(nuke.Tab_Knob("Deadline"))

    knob = nuke.Int_Knob("deadlineChunkSize", "Chunk Size")
    knob.setValue(0)
    node.addKnob(knob)

    knob = nuke.Int_Knob("deadlinePriority", "Priority")
    knob.setValue(50)
    node.addKnob(knob)


def get_deadline_knob_names():
    return ["Deadline", "deadlineChunkSize", "deadlinePriority"]


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

    def __init__(self,
                 root_node=None,
                 nodes=None,
                 **kwargs):
        self._project = kwargs.get(
            "project") or io.find_one({"type": "project"})
        self._asset = kwargs.get("asset_name") or api.Session["AVALON_ASSET"]
        self._asset_entity = pype.get_asset(self._asset)
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
        for v in [n for n in self._nodes
                  if "Viewer" in n.Class()]:
            v['viewerProcess'].setValue(str(viewer_dict["viewerProcess"]))
            if str(viewer_dict["viewerProcess"]) \
                    not in v['viewerProcess'].value():
                copy_inputs = v.dependencies()
                copy_knobs = {k: v[k].value() for k in v.knobs()
                              if k not in filter_knobs}

                # delete viewer with wrong settings
                erased_viewers.append(v['name'].value())
                nuke.delete(v)

                # create new viewer
                nv = nuke.createNode("Viewer")

                # connect to original inputs
                for i, n in enumerate(copy_inputs):
                    nv.setInput(i, n)

                # set coppied knobs
                for k, v in copy_knobs.items():
                    print(k, v)
                    nv[k].setValue(v)

                # set viewerProcess
                nv['viewerProcess'].setValue(str(viewer_dict["viewerProcess"]))

        if erased_viewers:
            log.warning(
                "Attention! Viewer nodes {} were erased."
                "It had wrong color profile".format(erased_viewers))

    def set_root_colorspace(self, root_dict):
        ''' Adds correct colorspace to root

        Arguments:
            root_dict (dict): adjustmensts from presets

        '''
        if not isinstance(root_dict, dict):
            msg = "set_root_colorspace(): argument should be dictionary"
            log.error(msg)
            nuke.message(msg)

        log.debug(">> root_dict: {}".format(root_dict))

        # first set OCIO
        if self._root_node["colorManagement"].value() \
                not in str(root_dict["colorManagement"]):
            self._root_node["colorManagement"].setValue(
                str(root_dict["colorManagement"]))
            log.debug("nuke.root()['{0}'] changed to: {1}".format(
                "colorManagement", root_dict["colorManagement"]))
            root_dict.pop("colorManagement")

        # second set ocio version
        if self._root_node["OCIO_config"].value() \
                not in str(root_dict["OCIO_config"]):
            self._root_node["OCIO_config"].setValue(
                str(root_dict["OCIO_config"]))
            log.debug("nuke.root()['{0}'] changed to: {1}".format(
                "OCIO_config", root_dict["OCIO_config"]))
            root_dict.pop("OCIO_config")

        # third set ocio custom path
        if root_dict.get("customOCIOConfigPath"):
            self._root_node["customOCIOConfigPath"].setValue(
                str(root_dict["customOCIOConfigPath"]).format(
                    **os.environ
                ).replace("\\", "/")
            )
            log.debug("nuke.root()['{}'] changed to: {}".format(
                "customOCIOConfigPath", root_dict["customOCIOConfigPath"]))
            root_dict.pop("customOCIOConfigPath")

        # then set the rest
        for knob, value in root_dict.items():
            if self._root_node[knob].value() not in value:
                self._root_node[knob].setValue(str(value))
                log.debug("nuke.root()['{}'] changed to: {}".format(
                    knob, value))

    def set_writes_colorspace(self, write_dict):
        ''' Adds correct colorspace to write node dict

        Arguments:
            write_dict (dict): nuke write node as dictionary

        '''
        # scene will have fixed colorspace following presets for the project
        if not isinstance(write_dict, dict):
            msg = "set_root_colorspace(): argument should be dictionary"
            log.error(msg)
            return

        from avalon.nuke import get_avalon_knob_data

        for node in nuke.allNodes():

            if node.Class() in ["Viewer", "Dot"]:
                continue

            # get data from avalon knob
            avalon_knob_data = get_avalon_knob_data(node, ["avalon:", "ak:"])

            if not avalon_knob_data:
                continue

            if avalon_knob_data["id"] != "pyblish.avalon.instance":
                continue

            # establish families
            families = [avalon_knob_data["family"]]
            if avalon_knob_data.get("families"):
                families.append(avalon_knob_data.get("families"))

            # except disabled nodes but exclude backdrops in test
            for fmly, knob in write_dict.items():
                write = None
                if (fmly in families):
                    # Add all nodes in group instances.
                    if node.Class() == "Group":
                        node.begin()
                        for x in nuke.allNodes():
                            if x.Class() == "Write":
                                write = x
                        node.end()
                    elif node.Class() == "Write":
                        write = node
                    else:
                        log.warning("Wrong write node Class")

                    write["colorspace"].setValue(str(knob["colorspace"]))
                    log.info(
                        "Setting `{0}` to `{1}`".format(
                            write.name(),
                            knob["colorspace"]))

    def set_reads_colorspace(self, reads):
        """ Setting colorspace to Read nodes

        Looping trought all read nodes and tries to set colorspace based
        on regex rules in presets
        """
        changes = dict()
        for n in nuke.allNodes():
            file = nuke.filename(n)
            if not n.Class() == "Read":
                continue

            # load nuke presets for Read's colorspace
            read_clrs_presets = get_colorspace_preset().get(
                "nuke", {}).get("read", {})

            # check if any colorspace presets for read is mathing
            preset_clrsp = next((read_clrs_presets[k]
                                 for k in read_clrs_presets
                                 if bool(re.search(k, file))),
                                None)
            log.debug(preset_clrsp)
            if preset_clrsp is not None:
                current = n["colorspace"].value()
                future = str(preset_clrsp)
                if current != future:
                    changes.update({
                        n.name(): {
                            "from": current,
                            "to": future
                        }
                    })
        log.debug(changes)
        if changes:
            msg = "Read nodes are not set to correct colospace:\n\n"
            for nname, knobs in changes.items():
                msg += str(
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
        ''' Setting colorpace following presets
        '''
        nuke_colorspace = get_colorspace_preset().get("nuke", None)

        try:
            self.set_root_colorspace(nuke_colorspace["root"])
        except AttributeError:
            msg = "set_colorspace(): missing `root` settings in template"

        try:
            self.set_viewers_colorspace(nuke_colorspace["viewer"])
        except AttributeError:
            msg = "set_colorspace(): missing `viewer` settings in template"
            nuke.message(msg)
            log.error(msg)

        try:
            self.set_writes_colorspace(nuke_colorspace["write"])
        except AttributeError:
            msg = "set_colorspace(): missing `write` settings in template"
            nuke.message(msg)
            log.error(msg)

        reads = nuke_colorspace.get("read")
        if reads:
            self.set_reads_colorspace(reads)

        try:
            for key in nuke_colorspace:
                log.debug("Preset's colorspace key: {}".format(key))
        except TypeError:
            msg = "Nuke is not in templates! Contact your supervisor!"
            nuke.message(msg)
            log.error(msg)

    def reset_frame_range_handles(self):
        """Set frame range to current asset"""

        if "data" not in self._asset_entity:
            msg = "Asset {} don't have set any 'data'".format(self._asset)
            log.warning(msg)
            nuke.message(msg)
            return
        data = self._asset_entity["data"]

        log.debug("__ asset data: `{}`".format(data))

        missing_cols = []
        check_cols = ["fps", "frameStart", "frameEnd",
                      "handleStart", "handleEnd"]

        for col in check_cols:
            if col not in data:
                missing_cols.append(col)

        if len(missing_cols) > 0:
            missing = ", ".join(missing_cols)
            msg = "'{}' are not set for asset '{}'!".format(
                missing, self._asset)
            log.warning(msg)
            nuke.message(msg)
            return

        # get handles values
        handle_start = data["handleStart"]
        handle_end = data["handleEnd"]

        fps = data["fps"]
        frame_start = int(data["frameStart"]) - handle_start
        frame_end = int(data["frameEnd"]) + handle_end

        self._root_node["lock_range"].setValue(False)
        self._root_node["fps"].setValue(fps)
        self._root_node["first_frame"].setValue(frame_start)
        self._root_node["last_frame"].setValue(frame_end)
        self._root_node["lock_range"].setValue(True)

        # setting active viewers
        try:
            nuke.frame(int(data["frameStart"]))
        except Exception as e:
            log.warning("no viewer in scene: `{}`".format(e))

        range = '{0}-{1}'.format(
            int(data["frameStart"]),
            int(data["frameEnd"]))

        for node in nuke.allNodes(filter="Viewer"):
            node['frame_range'].setValue(range)
            node['frame_range_lock'].setValue(True)
            node['frame_range'].setValue(range)
            node['frame_range_lock'].setValue(True)

        # adding handle_start/end to root avalon knob
        if not avalon.nuke.imprint(self._root_node, {
            "handleStart": int(handle_start),
            "handleEnd": int(handle_end)
        }):
            log.warning("Cannot set Avalon knob to Root node!")

    def reset_resolution(self):
        """Set resolution to project resolution."""
        log.info("Reseting resolution")
        project = io.find_one({"type": "project"})
        asset = api.Session["AVALON_ASSET"]
        asset = io.find_one({"name": asset, "type": "asset"})
        asset_data = asset.get('data', {})

        data = {
            "width": int(asset_data.get(
                'resolutionWidth',
                asset_data.get('resolution_width'))),
            "height": int(asset_data.get(
                'resolutionHeight',
                asset_data.get('resolution_height'))),
            "pixel_aspect": asset_data.get(
                'pixelAspect',
                asset_data.get('pixel_aspect', 1)),
            "name": project["name"]
        }

        if any(x for x in data.values() if x is None):
            msg = ("Missing set shot attributes in DB."
                   "\nContact your supervisor!."
                   "\n\nWidth: `{width}`"
                   "\nHeight: `{height}`"
                   "\nPixel Asspect: `{pixel_aspect}`").format(**data)
            log.error(msg)
            nuke.message(msg)

        bbox = self._asset_entity.get('data', {}).get('crop')

        if bbox:
            try:
                x, y, r, t = bbox.split(".")
                data.update(
                    {
                        "x": int(x),
                        "y": int(y),
                        "r": int(r),
                        "t": int(t),
                    }
                )
            except Exception as e:
                bbox = None
                msg = ("{}:{} \nFormat:Crop need to be set with dots, "
                       "example: 0.0.1920.1080, "
                       "/nSetting to default").format(__name__, e)
                log.error(msg)
                nuke.message(msg)

        existing_format = None
        for format in nuke.formats():
            if data["name"] == format.name():
                existing_format = format
                break

        if existing_format:
            # Enforce existing format to be correct.
            existing_format.setWidth(data["width"])
            existing_format.setHeight(data["height"])
            existing_format.setPixelAspect(data["pixel_aspect"])

            if bbox:
                existing_format.setX(data["x"])
                existing_format.setY(data["y"])
                existing_format.setR(data["r"])
                existing_format.setT(data["t"])
        else:
            format_string = self.make_format_string(**data)
            log.info("Creating new format: {}".format(format_string))
            nuke.addFormat(format_string)

        nuke.root()["format"].setValue(data["name"])
        log.info("Format is set.")

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
        anatomy = get_anatomy()
        work_template = anatomy.templates["work"]["path"]
        projects_root = anatomy.root_value_for_template(work_template)
        work_dir = os.getenv("AVALON_WORKDIR")
        asset = os.getenv("AVALON_ASSET")
        project = os.getenv("AVALON_PROJECT")
        hierarchy = os.getenv("AVALON_HIERARCHY")
        favorite_items = OrderedDict()

        # project
        favorite_items.update({"Project dir": os.path.join(
            projects_root, project).replace("\\", "/")})
        # shot
        favorite_items.update({"Shot dir": os.path.join(
            projects_root, project,
            hierarchy, asset).replace("\\", "/")})
        # workdir
        favorite_items.update({"Work dir": work_dir})

        set_context_favorites(favorite_items)


def get_hierarchical_attr(entity, attr, default=None):
    attr_parts = attr.split('.')
    value = entity
    for part in attr_parts:
        value = value.get(part)
        if not value:
            break

    if value or entity['type'].lower() == 'project':
        return value

    parent_id = entity['parent']
    if (
        entity['type'].lower() == 'asset'
        and entity.get('data', {}).get('visualParent')
    ):
        parent_id = entity['data']['visualParent']

    parent = io.find_one({'_id': parent_id})

    return get_hierarchical_attr(parent, attr)


def get_write_node_template_attr(node):
    ''' Gets all defined data from presets

    '''
    # get avalon data from node
    data = dict()
    data['avalon'] = avalon.nuke.get_avalon_knob_data(
        node, ['avalon:', 'ak:'])
    data_preset = {
        "class": data['avalon']['family'],
        "families": data['avalon']['families'],
        "preset": data['avalon']['families']  # omit < 2.0.0v
    }

    # get template data
    nuke_dataflow_writes = get_node_dataflow_preset(**data_preset)
    nuke_colorspace_writes = get_node_colorspace_preset(**data_preset)

    # collecting correct data
    correct_data = OrderedDict({
        "file": get_render_path(node)
    })

    # adding dataflow template
    {correct_data.update({k: v})
     for k, v in nuke_dataflow_writes.items()
     if k not in ["_id", "_previous"]}

    # adding colorspace template
    {correct_data.update({k: v})
     for k, v in nuke_colorspace_writes.items()}

    # fix badly encoded data
    return avalon.nuke.lib.fix_data_for_node_create(correct_data)


class ExporterReview:
    """
    Base class object for generating review data from Nuke

    Args:
        klass (pyblish.plugin): pyblish plugin parent
        instance (pyblish.instance): instance of pyblish context

    """
    _temp_nodes = []
    data = dict({
        "representations": list()
    })

    def __init__(self,
                 klass,
                 instance
                 ):

        self.log = klass.log
        self.instance = instance
        self.path_in = self.instance.data.get("path", None)
        self.staging_dir = self.instance.data["stagingDir"]
        self.collection = self.instance.data.get("collection", None)

    def get_file_info(self):
        if self.collection:
            self.log.debug("Collection: `{}`".format(self.collection))
            # get path
            self.fname = os.path.basename(self.collection.format(
                "{head}{padding}{tail}"))
            self.fhead = self.collection.format("{head}")

            # get first and last frame
            self.first_frame = min(self.collection.indexes)
            self.last_frame = max(self.collection.indexes)
            if "slate" in self.instance.data["families"]:
                self.first_frame += 1
        else:
            self.fname = os.path.basename(self.path_in)
            self.fhead = os.path.splitext(self.fname)[0] + "."
            self.first_frame = self.instance.data.get("frameStartHandle", None)
            self.last_frame = self.instance.data.get("frameEndHandle", None)

        if "#" in self.fhead:
            self.fhead = self.fhead.replace("#", "")[:-1]

    def get_representation_data(self, tags=None, range=False):
        add_tags = []
        if tags:
            add_tags = tags

        repre = {
            'name': self.name,
            'ext': self.ext,
            'files': self.file,
            "stagingDir": self.staging_dir,
            "tags": [self.name.replace("_", "-")] + add_tags
        }

        if range:
            repre.update({
                "frameStart": self.first_frame,
                "frameEnd": self.last_frame,
            })

        self.data["representations"].append(repre)

    def get_view_process_node(self):
        """
        Will get any active view process.

        Arguments:
            self (class): in object definition

        Returns:
            nuke.Node: copy node of Input Process node
        """
        anlib.reset_selection()
        ipn_orig = None
        for v in [n for n in nuke.allNodes()
                  if "Viewer" == n.Class()]:
            ip = v['input_process'].getValue()
            ipn = v['input_process_node'].getValue()
            if "VIEWER_INPUT" not in ipn and ip:
                ipn_orig = nuke.toNode(ipn)
                ipn_orig.setSelected(True)

        if ipn_orig:
            # copy selected to clipboard
            nuke.nodeCopy('%clipboard%')
            # reset selection
            anlib.reset_selection()
            # paste node and selection is on it only
            nuke.nodePaste('%clipboard%')
            # assign to variable
            ipn = nuke.selectedNode()

            return ipn

    def clean_nodes(self):
        for node in self._temp_nodes:
            nuke.delete(node)
        self.log.info("Deleted nodes...")


class ExporterReviewLut(ExporterReview):
    """
    Generator object for review lut from Nuke

    Args:
        klass (pyblish.plugin): pyblish plugin parent
        instance (pyblish.instance): instance of pyblish context


    """
    def __init__(self,
                 klass,
                 instance,
                 name=None,
                 ext=None,
                 cube_size=None,
                 lut_size=None,
                 lut_style=None):
        # initialize parent class
        ExporterReview.__init__(self, klass, instance)

        # deal with now lut defined in viewer lut
        if hasattr(klass, "viewer_lut_raw"):
            self.viewer_lut_raw = klass.viewer_lut_raw
        else:
            self.viewer_lut_raw = False

        self.name = name or "baked_lut"
        self.ext = ext or "cube"
        self.cube_size = cube_size or 32
        self.lut_size = lut_size or 1024
        self.lut_style = lut_style or "linear"

        # set frame start / end and file name to self
        self.get_file_info()

        self.log.info("File info was set...")

        self.file = self.fhead + self.name + ".{}".format(self.ext)
        self.path = os.path.join(
            self.staging_dir, self.file).replace("\\", "/")

    def generate_lut(self):
        # ---------- start nodes creation

        # CMSTestPattern
        cms_node = nuke.createNode("CMSTestPattern")
        cms_node["cube_size"].setValue(self.cube_size)
        # connect
        self._temp_nodes.append(cms_node)
        self.previous_node = cms_node
        self.log.debug("CMSTestPattern...   `{}`".format(self._temp_nodes))

        # Node View Process
        ipn = self.get_view_process_node()
        if ipn is not None:
            # connect
            ipn.setInput(0, self.previous_node)
            self._temp_nodes.append(ipn)
            self.previous_node = ipn
            self.log.debug("ViewProcess...   `{}`".format(self._temp_nodes))

        if not self.viewer_lut_raw:
            # OCIODisplay
            dag_node = nuke.createNode("OCIODisplay")
            # connect
            dag_node.setInput(0, self.previous_node)
            self._temp_nodes.append(dag_node)
            self.previous_node = dag_node
            self.log.debug("OCIODisplay...   `{}`".format(self._temp_nodes))

        # GenerateLUT
        gen_lut_node = nuke.createNode("GenerateLUT")
        gen_lut_node["file"].setValue(self.path)
        gen_lut_node["file_type"].setValue(".{}".format(self.ext))
        gen_lut_node["lut1d"].setValue(self.lut_size)
        gen_lut_node["style1d"].setValue(self.lut_style)
        # connect
        gen_lut_node.setInput(0, self.previous_node)
        self._temp_nodes.append(gen_lut_node)
        self.log.debug("GenerateLUT...   `{}`".format(self._temp_nodes))

        # ---------- end nodes creation

        # Export lut file
        nuke.execute(
            gen_lut_node.name(),
            int(self.first_frame),
            int(self.first_frame))

        self.log.info("Exported...")

        # ---------- generate representation data
        self.get_representation_data()

        self.log.debug("Representation...   `{}`".format(self.data))

        # ---------- Clean up
        self.clean_nodes()

        return self.data


class ExporterReviewMov(ExporterReview):
    """
    Metaclass for generating review mov files

    Args:
        klass (pyblish.plugin): pyblish plugin parent
        instance (pyblish.instance): instance of pyblish context

    """
    def __init__(self,
                 klass,
                 instance,
                 name=None,
                 ext=None,
                 ):
        # initialize parent class
        ExporterReview.__init__(self, klass, instance)

        # passing presets for nodes to self
        if hasattr(klass, "nodes"):
            self.nodes = klass.nodes
        else:
            self.nodes = {}

        # deal with now lut defined in viewer lut
        self.viewer_lut_raw = klass.viewer_lut_raw
        self.bake_colorspace_fallback = klass.bake_colorspace_fallback
        self.bake_colorspace_main = klass.bake_colorspace_main

        self.name = name or "baked"
        self.ext = ext or "mov"

        # set frame start / end and file name to self
        self.get_file_info()

        self.log.info("File info was set...")

        self.file = self.fhead + self.name + ".{}".format(self.ext)
        self.path = os.path.join(
            self.staging_dir, self.file).replace("\\", "/")

    def render(self, render_node_name):
        self.log.info("Rendering...  ")
        # Render Write node
        nuke.execute(
            render_node_name,
            int(self.first_frame),
            int(self.last_frame))

        self.log.info("Rendered...")

    def save_file(self):
        import shutil
        with anlib.maintained_selection():
            self.log.info("Saving nodes as file...  ")
            # create nk path
            path = os.path.splitext(self.path)[0] + ".nk"
            # save file to the path
            shutil.copyfile(self.instance.context.data["currentFile"], path)

        self.log.info("Nodes exported...")
        return path

    def generate_mov(self, farm=False):
        # ---------- start nodes creation

        # Read node
        r_node = nuke.createNode("Read")
        r_node["file"].setValue(self.path_in)
        r_node["first"].setValue(self.first_frame)
        r_node["origfirst"].setValue(self.first_frame)
        r_node["last"].setValue(self.last_frame)
        r_node["origlast"].setValue(self.last_frame)
        # connect
        self._temp_nodes.append(r_node)
        self.previous_node = r_node
        self.log.debug("Read...   `{}`".format(self._temp_nodes))

        # View Process node
        ipn = self.get_view_process_node()
        if ipn is not None:
            # connect
            ipn.setInput(0, self.previous_node)
            self._temp_nodes.append(ipn)
            self.previous_node = ipn
            self.log.debug("ViewProcess...   `{}`".format(self._temp_nodes))

        if not self.viewer_lut_raw:
            colorspaces = [
                self.bake_colorspace_main, self.bake_colorspace_fallback
            ]

            if any(colorspaces):
                # OCIOColorSpace with controled output
                dag_node = nuke.createNode("OCIOColorSpace")
                self._temp_nodes.append(dag_node)
                for c in colorspaces:
                    test = dag_node["out_colorspace"].setValue(str(c))
                    if test:
                        self.log.info(
                            "Baking in colorspace...   `{}`".format(c))
                        break

                if not test:
                    dag_node = nuke.createNode("OCIODisplay")
            else:
                # OCIODisplay
                dag_node = nuke.createNode("OCIODisplay")

            # connect
            dag_node.setInput(0, self.previous_node)
            self._temp_nodes.append(dag_node)
            self.previous_node = dag_node
            self.log.debug("OCIODisplay...   `{}`".format(self._temp_nodes))

        # Write node
        write_node = nuke.createNode("Write")
        self.log.debug("Path: {}".format(self.path))
        write_node["file"].setValue(self.path)
        write_node["file_type"].setValue(self.ext)
        write_node["meta_codec"].setValue("ap4h")
        write_node["mov64_codec"].setValue("ap4h")
        write_node["mov64_write_timecode"].setValue(1)
        write_node["raw"].setValue(1)
        # connect
        write_node.setInput(0, self.previous_node)
        self._temp_nodes.append(write_node)
        self.log.debug("Write...   `{}`".format(self._temp_nodes))
        # ---------- end nodes creation

        # ---------- render or save to nk
        if farm:
            nuke.scriptSave()
            path_nk = self.save_file()
            self.data.update({
                "bakeScriptPath": path_nk,
                "bakeWriteNodeName": write_node.name(),
                "bakeRenderPath": self.path
            })
        else:
            self.render(write_node.name())
            # ---------- generate representation data
            self.get_representation_data(
                tags=["review", "delete"],
                range=True
            )

        self.log.debug("Representation...   `{}`".format(self.data))

        # ---------- Clean up
        self.clean_nodes()
        nuke.scriptSave()
        return self.data


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


def find_free_space_to_paste_nodes(
        nodes,
        group=nuke.root(),
        direction="right",
        offset=300):
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
