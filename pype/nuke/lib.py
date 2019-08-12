import os
import sys
from collections import OrderedDict
from pprint import pprint
from avalon import api, io, lib
import avalon.nuke
import pype.api as pype
import nuke
from .templates import (
    get_colorspace_preset,
    get_node_dataflow_preset,
    get_node_colorspace_preset
)

from pypeapp import Logger
log = Logger().get_logger(__name__, "nuke")

self = sys.modules[__name__]
self._project = None


def onScriptLoad():
    ''' Callback for ffmpeg support
    '''
    if nuke.env['LINUX']:
        nuke.tcl('load ffmpegReader')
        nuke.tcl('load ffmpegWriter')
    else:
        nuke.tcl('load movReader')
        nuke.tcl('load movWriter')


def checkInventoryVersions():
    """
    Actiual version idetifier of Loaded containers

    Any time this function is run it will check all nodes and filter only
    Loader nodes for its version. It will get all versions from database
    and check if the node is having actual version. If not then it will color
    it to red.
    """
    # TODO: make it for all nodes not just Read (Loader

    # get all Loader nodes by avalon attribute metadata
    for each in nuke.allNodes():
        if each.Class() == 'Read':
            container = avalon.nuke.parse_container(each)

            if container:
                node = container["_node"]
                avalon_knob_data = avalon.nuke.get_avalon_knob_data(node)

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
    # TODO: make it work with new write node group
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
            avalon_knob_data = avalon.nuke.get_avalon_knob_data(each)

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
                    "Write node: `{}` has no version in path: {}".format(each.name(), e))


def version_up_script():
    ''' Raising working script's version
    '''
    import nukescripts
    nukescripts.script_and_write_nodes_version_up()


def get_render_path(node):
    ''' Generate Render path from presets regarding avalon knob data
    '''
    data = dict()
    data['avalon'] = avalon.nuke.get_avalon_knob_data(node)

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

    from .templates import (
        get_anatomy
    )
    # TODO: remove get_anatomy and import directly Anatomy() here

    anatomy = get_anatomy()
    log.debug("__ anatomy.templates: {}".format(anatomy.templates))

    # TODO: perhaps should be in try!
    padding = int(anatomy.templates['render']['padding'])
    version = data.get("version", None)
    if not version:
        file = script_name()
        data["version"] = pype.get_version_from_path(file)
    project_document = pype.get_project()
    data.update({
        "root": api.Session["AVALON_PROJECTS"],
        "subset": data["avalon"]["subset"],
        "asset": data["avalon"]["asset"],
        "task": api.Session["AVALON_TASK"].lower(),
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
    label = "Create Read"
    value = "import write_to_read;write_to_read.write_to_read(nuke.thisNode())"
    k = nuke.PyScript_Knob(name, label, value)
    k.setFlag(0x1000)
    node.addKnob(k)

def create_write_node(name, data, prenodes=None):
    ''' Creating write node which is group node

    Arguments:
        name (str): name of node
        data (dict): data to be imprinted
        prenodes (list, optional): list of lists, definitions for nodes
                                to be created before write

    Example:
        prenodes = [(
            "NameNode",  # string
            "NodeClass",  # string
            (   # OrderDict: knob and values pairs
                ("knobName", "knobValue"),
                ("knobName", "knobValue")
            ),
            (   # list inputs
                "firstPrevNodeName",
                "secondPrevNodeName"
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
        log.error("problem with resolving anatomy tepmlate: {}".format(e))

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
    {_data.update({k: v})
     for k, v in nuke_dataflow_writes.items()
     if k not in ["_id", "_previous"]}

    # adding dataflow template
    {_data.update({k: v})
     for k, v in nuke_colorspace_writes.items()}

    _data = avalon.nuke.lib.fix_data_for_node_create(_data)

    log.debug(_data)

    _data["frame_range"] = data.get("frame_range", None)

    # todo: hange this to new way
    GN = nuke.createNode("Group", "name {}".format(name))

    prev_node = None
    with GN:
        # creating pre-write nodes `prenodes`
        if prenodes:
            for name, klass, properties, set_input_to in prenodes:
                # create node
                now_node = nuke.createNode(klass, "name {}".format(name))

                # add data to knob
                for k, v in properties:
                    if k and v:
                        now_node[k].serValue(str(v))

                # connect to previous node
                if set_input_to:
                    if isinstance(set_input_to, (tuple or list)):
                        for i, node_name in enumerate(set_input_to):
                            input_node = nuke.toNode(node_name)
                            now_node.setInput(1, input_node)
                    elif isinstance(set_input_to, str):
                        input_node = nuke.toNode(set_input_to)
                        now_node.setInput(0, input_node)
                else:
                    now_node.setInput(0, prev_node)

                # swith actual node to previous
                prev_node = now_node
        else:
            prev_node = nuke.createNode("Input", "name rgba")


        # creating write node
        now_node = avalon.nuke.lib.add_write_node("inside_{}".format(name),
                                                  **_data
                                                  )
        write_node = now_node
        # connect to previous node
        now_node.setInput(0, prev_node)

        # swith actual node to previous
        prev_node = now_node

        now_node = nuke.createNode("Output", "name write")

        # connect to previous node
        now_node.setInput(0, prev_node)

    # imprinting group node
    GN = avalon.nuke.imprint(GN, data["avalon"])


    divider = nuke.Text_Knob('')
    GN.addKnob(divider)

    add_rendering_knobs(GN)

    # adding write to read button
    add_button_write_to_read(GN)
    
    divider = nuke.Text_Knob('')
    GN.addKnob(divider)

    # set tile color
    tile_color = _data.get("tile_color", "0xff0000ff")
    GN["tile_color"].setValue(tile_color)


    # add render button
    lnk = nuke.Link_Knob("Render")
    lnk.makeLink(write_node.name(), "Render")
    lnk.setName("Render")
    GN.addKnob(lnk)

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


def set_viewers_colorspace(viewer):
    ''' Adds correct colorspace to viewer

    Arguments:
        viewer (obj): nuke viewer node object to be fixed

    '''
    assert isinstance(viewer, dict), log.error(
        "set_viewers_colorspace(): argument should be dictionary")

    filter_knobs = [
        "viewerProcess",
        "wipe_position"
    ]
    viewers = [n for n in nuke.allNodes() if n.Class() == 'Viewer']
    erased_viewers = []

    for v in viewers:
        v['viewerProcess'].setValue(str(viewer["viewerProcess"]))
        if str(viewer["viewerProcess"]) not in v['viewerProcess'].value():
            copy_inputs = v.dependencies()
            copy_knobs = {k: v[k].value() for k in v.knobs()
                          if k not in filter_knobs}
            pprint(copy_knobs)
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
            nv['viewerProcess'].setValue(str(viewer["viewerProcess"]))

    if erased_viewers:
        log.warning(
            "Attention! Viewer nodes {} were erased."
            "It had wrong color profile".format(erased_viewers))


def set_root_colorspace(root_dict):
    ''' Adds correct colorspace to root

    Arguments:
        root_dict (dict): nuke root node as dictionary

    '''
    assert isinstance(root_dict, dict), log.error(
        "set_root_colorspace(): argument should be dictionary")

    # first set OCIO
    if nuke.root()["colorManagement"].value() not in str(root_dict["colorManagement"]):
        nuke.root()["colorManagement"].setValue(
            str(root_dict["colorManagement"]))

    # second set ocio version
    if nuke.root()["OCIO_config"].value() not in str(root_dict["OCIO_config"]):
        nuke.root()["OCIO_config"].setValue(str(root_dict["OCIO_config"]))

    # then set the rest
    for knob, value in root_dict.items():
        if nuke.root()[knob].value() not in value:
            nuke.root()[knob].setValue(str(value))
            log.debug("nuke.root()['{}'] changed to: {}".format(knob, value))


def set_writes_colorspace(write_dict):
    ''' Adds correct colorspace to write node dict

    Arguments:
        write_dict (dict): nuke write node as dictionary

    '''
    # TODO: complete this function so any write node in scene will have fixed colorspace following presets for the project
    assert isinstance(write_dict, dict), log.error(
        "set_root_colorspace(): argument should be dictionary")

    log.debug("__ set_writes_colorspace(): {}".format(write_dict))


def set_colorspace():
    ''' Setting colorpace following presets
    '''
    nuke_colorspace = get_colorspace_preset().get("nuke", None)

    try:
        set_root_colorspace(nuke_colorspace["root"])
    except AttributeError:
        log.error(
            "set_colorspace(): missing `root` settings in template")
    try:
        set_viewers_colorspace(nuke_colorspace["viewer"])
    except AttributeError:
        log.error(
            "set_colorspace(): missing `viewer` settings in template")
    try:
        set_writes_colorspace(nuke_colorspace["write"])
    except AttributeError:
        log.error(
            "set_colorspace(): missing `write` settings in template")

    try:
        for key in nuke_colorspace:
            log.debug("Preset's colorspace key: {}".format(key))
    except TypeError:
        log.error("Nuke is not in templates! \n\n\n"
                  "contact your supervisor!")


def reset_frame_range_handles():
    """Set frame range to current asset"""

    root = nuke.root()
    name = api.Session["AVALON_ASSET"]
    asset_entity = pype.get_asset(name)

    if "data" not in asset_entity:
        msg = "Asset {} don't have set any 'data'".format(name)
        log.warning(msg)
        nuke.message(msg)
        return
    data = asset_entity["data"]

    missing_cols = []
    check_cols = ["fps", "frameStart", "frameEnd", "handleStart", "handleEnd"]

    for col in check_cols:
        if col not in data:
            missing_cols.append(col)

    if len(missing_cols) > 0:
        missing = ", ".join(missing_cols)
        msg = "'{}' are not set for asset '{}'!".format(missing, name)
        log.warning(msg)
        nuke.message(msg)
        return

    # get handles values
    handle_start = asset_entity["data"]["handleStart"]
    handle_end = asset_entity["data"]["handleEnd"]

    fps = asset_entity["data"]["fps"]
    frame_start = int(asset_entity["data"]["frameStart"]) - handle_start
    frame_end = int(asset_entity["data"]["frameEnd"]) + handle_end

    root["fps"].setValue(fps)
    root["first_frame"].setValue(frame_start)
    root["last_frame"].setValue(frame_end)

    # setting active viewers
    nuke.frame(int(asset_entity["data"]["frameStart"]))

    range = '{0}-{1}'.format(
        int(asset_entity["data"]["frameStart"]),
        int(asset_entity["data"]["frameEnd"]))

    for node in nuke.allNodes(filter="Viewer"):
        node['frame_range'].setValue(range)
        node['frame_range_lock'].setValue(True)
        node['frame_range'].setValue(range)
        node['frame_range_lock'].setValue(True)

    # adding handle_start/end to root avalon knob
    if not avalon.nuke.set_avalon_knob_data(root, {
        "handleStart": int(handle_start),
        "handleEnd": int(handle_end)
    }):
        log.warning("Cannot set Avalon knob to Root node!")


def reset_resolution():
    """Set resolution to project resolution."""
    log.info("Reseting resolution")
    project = io.find_one({"type": "project"})
    asset = api.Session["AVALON_ASSET"]
    asset = io.find_one({"name": asset, "type": "asset"})

    width = asset.get('data', {}).get("resolutionWidth")
    height = asset.get('data', {}).get("resolutionHeight")
    pixel_aspect = asset.get('data', {}).get("pixelAspect")

    if any(not x for x in [width, height, pixel_aspect]):
        log.error("Missing set shot attributes in DB. \nContact your supervisor!. \n\nWidth: `{0}` \nHeight: `{1}` \nPixel Asspect: `{2}`".format(
            width, height, pixel_aspect))
        return

    bbox = asset.get('data', {}).get('crop')

    if bbox:
        try:
            x, y, r, t = bbox.split(".")
        except Exception as e:
            bbox = None
            log.error("{}: {} \nFormat:Crop need to be set with dots, example: "
                      "0.0.1920.1080, /nSetting to default".format(__name__, e))

    used_formats = list()
    for f in nuke.formats():
        if project["name"] in str(f.name()):
            used_formats.append(f)
        else:
            format_name = project["name"] + "_1"

    crnt_fmt_str = ""
    if used_formats:
        check_format = used_formats[-1]
        format_name = "{}_{}".format(
            project["name"],
            int(used_formats[-1].name()[-1]) + 1
        )
        log.info(
            "Format exists: {}. "
            "Will create new: {}...".format(
                used_formats[-1].name(),
                format_name)
        )
        crnt_fmt_kargs = {
            "width": (check_format.width()),
            "height": (check_format.height()),
            "pixelAspect": float(check_format.pixelAspect())
        }
        if bbox:
            crnt_fmt_kargs.update({
                "x": int(check_format.x()),
                "y": int(check_format.y()),
                "r": int(check_format.r()),
                "t": int(check_format.t()),
            })
        crnt_fmt_str = make_format_string(**crnt_fmt_kargs)

    new_fmt_kargs = {
        "width": int(width),
        "height": int(height),
        "pixelAspect": float(pixel_aspect),
        "project_name": format_name
    }
    if bbox:
        new_fmt_kargs.update({
            "x": int(x),
            "y": int(y),
            "r": int(r),
            "t": int(t),
        })

    new_fmt_str = make_format_string(**new_fmt_kargs)

    if new_fmt_str not in crnt_fmt_str:
        make_format(frm_str=new_fmt_str,
                    project_name=new_fmt_kargs["project_name"])

        log.info("Format is set")


def make_format_string(**args):
    if args.get("r"):
        return (
            "{width} "
            "{height} "
            "{x} "
            "{y} "
            "{r} "
            "{t} "
            "{pixelAspect:.2f}".format(**args)
        )
    else:
        return (
            "{width} "
            "{height} "
            "{pixelAspect:.2f}".format(**args)
        )


def make_format(**args):
    log.info("Format does't exist, will create: \n{}".format(args))
    nuke.addFormat("{frm_str} "
                   "{project_name}".format(**args))
    nuke.root()["format"].setValue("{project_name}".format(**args))


def set_context_settings():
    # replace reset resolution from avalon core to pype's
    reset_resolution()
    # replace reset resolution from avalon core to pype's
    reset_frame_range_handles()
    # add colorspace menu item
    set_colorspace()


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
    data['avalon'] = avalon.nuke.get_avalon_knob_data(node)
    data_preset = {
        "class": data['avalon']['family'],
        "preset": data['avalon']['families']
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
