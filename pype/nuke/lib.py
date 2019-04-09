import sys
from collections import OrderedDict
from pprint import pprint
from avalon.vendor.Qt import QtGui
from avalon import api, io, lib
import avalon.nuke
import pype.api as pype
import nuke

from pypeapp import Logger
log = Logger().get_logger(__name__, "nuke")

self = sys.modules[__name__]
self._project = None


def onScriptLoad():
    if nuke.env['LINUX']:
        nuke.tcl('load ffmpegReader')
        nuke.tcl('load ffmpegWriter')
    else:
        nuke.tcl('load movReader')
        nuke.tcl('load movWriter')


def writes_version_sync():
    try:
        rootVersion = pype.get_version_from_path(nuke.root().name())
        padding = len(rootVersion)
        new_version = str("{" + ":0>{}".format(padding) + "}").format(
            int(rootVersion)
        )
        log.info("new_version: {}".format(new_version))
    except Exception:
        return

    for each in nuke.allNodes():
        if each.Class() == 'Write':
            avalon_knob_data = get_avalon_knob_data(each)

            try:
                if avalon_knob_data['families'] not in ["render"]:
                    log.info(avalon_knob_data['families'])
                    continue

                node_file = each['file'].value()
                log.info("node_file: {}".format(node_file))

                node_version = pype.get_version_from_path(node_file)
                log.info("node_version: {}".format(node_version))

                node_new_file = node_file.replace(node_version, new_version)
                each['file'].setValue(node_new_file)
            except Exception as e:
                log.debug("Write node: `{}` has no version in path: {}".format(each.name(), e))


def version_up_script():
    import nukescripts
    nukescripts.script_and_write_nodes_version_up()


def format_anatomy(data):
    from .templates import (
        get_anatomy
    )
    file = script_name()

    anatomy = get_anatomy()

    # TODO: perhaps should be in try!
    padding = anatomy.render.padding

    data.update({
        "hierarchy": pype.get_hierarchy(),
        "frame": "#"*padding,
        "version": pype.get_version_from_path(file)
    })

    # log.info("format_anatomy:anatomy: {}".format(anatomy))
    return anatomy.format(data)


def script_name():
    return nuke.root().knob('name').value()


def create_write_node(name, data):
    from .templates import (
        get_dataflow,
        get_colorspace
    )
    nuke_dataflow_writes = get_dataflow(**data)
    nuke_colorspace_writes = get_colorspace(**data)
    application = lib.get_application(os.environ["AVALON_APP_NAME"])
    try:
        anatomy_filled = format_anatomy({
            "subset": data["avalon"]["subset"],
            "asset": data["avalon"]["asset"],
            "task": pype.get_task(),
            "family": data["avalon"]["family"],
            "project": {"name": pype.get_project_name(),
                        "code": pype.get_project_code()},
            "representation": nuke_dataflow_writes.file_type,
            "app": application["application_dir"],
        })
    except Exception as e:
        log.error("problem with resolving anatomy tepmlate: {}".format(e))

    log.debug("anatomy_filled.render: {}".format(anatomy_filled.render))

    _data = OrderedDict({
        "file": str(anatomy_filled.render.path).replace("\\", "/")
    })

    # adding dataflow template
    {_data.update({k: v})
     for k, v in nuke_dataflow_writes.items()
     if k not in ["id", "previous"]}

    # adding dataflow template
    {_data.update({k: v})
     for k, v in nuke_colorspace_writes.items()}

    _data = avalon.nuke.lib.fix_data_for_node_create(_data)

    log.debug(_data)

    _data["frame_range"] = data.get("frame_range", None)

    instance = avalon.nuke.lib.add_write_node(
        name,
        **_data
    )
    instance = avalon.nuke.lib.imprint(instance, data["avalon"])
    add_rendering_knobs(instance)
    return instance


def add_rendering_knobs(node):
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
    assert isinstance(viewer, dict), log.error(
        "set_viewers_colorspace(): argument should be dictionary")

    filter_knobs = [
        "viewerProcess",
        "wipe_position"
    ]
    viewers = [n for n in nuke.allNodes() if n.Class() == 'Viewer']
    erased_viewers = []

    for v in viewers:
        v['viewerProcess'].setValue(str(viewer.viewerProcess))
        if str(viewer.viewerProcess) not in v['viewerProcess'].value():
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
            nv['viewerProcess'].setValue(str(viewer.viewerProcess))

    if erased_viewers:
        log.warning(
            "Attention! Viewer nodes {} were erased."
            "It had wrong color profile".format(erased_viewers))


def set_root_colorspace(root_dict):
    assert isinstance(root_dict, dict), log.error(
        "set_root_colorspace(): argument should be dictionary")
    for knob, value in root_dict.items():
        if nuke.root()[knob].value() not in value:
            nuke.root()[knob].setValue(str(value))
            log.info("nuke.root()['{}'] changed to: {}".format(knob, value))


def set_writes_colorspace(write_dict):
    assert isinstance(write_dict, dict), log.error(
        "set_root_colorspace(): argument should be dictionary")
    log.info("set_writes_colorspace(): {}".format(write_dict))


def set_colorspace():
    from pype import api as pype

    nuke_colorspace = getattr(pype.Colorspace, "nuke", None)

    try:
        set_root_colorspace(nuke_colorspace.root)
    except AttributeError:
        log.error(
            "set_colorspace(): missing `root` settings in template")
    try:
        set_viewers_colorspace(nuke_colorspace.viewer)
    except AttributeError:
        log.error(
            "set_colorspace(): missing `viewer` settings in template")
    try:
        set_writes_colorspace(nuke_colorspace.write)
    except AttributeError:
        log.error(
            "set_colorspace(): missing `write` settings in template")

    try:
        for key in nuke_colorspace:
            log.info("{}".format(key))
    except TypeError:
        log.error("Nuke is not in templates! \n\n\n"
                  "contact your supervisor!")


def get_avalon_knob_data(node):
    import toml
    try:
        data = toml.loads(node['avalon'].value())
    except Exception:
        return None
    return data


def reset_resolution():
    """Set resolution to project resolution."""
    log.info("Reseting resolution")
    project = io.find_one({"type": "project"})
    asset = api.Session["AVALON_ASSET"]
    asset = io.find_one({"name": asset, "type": "asset"})

    try:
        width = asset["data"].get("resolution_width", 1920)
        height = asset["data"].get("resolution_height", 1080)
        pixel_aspect = asset["data"].get("pixel_aspect", 1)
        bbox = asset["data"].get("crop", "0.0.1920.1080")

        try:
            x, y, r, t = bbox.split(".")
        except Exception as e:
            x = 0
            y = 0
            r = width
            t = height
            log.error("{}: {} \nFormat:Crop need to be set with dots, example: "
                      "0.0.1920.1080, /nSetting to default".format(__name__, e))

    except KeyError:
        log.warning(
            "No resolution information found for \"{0}\".".format(
                project["name"]
            )
        )
        return

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
            int(used_formats[-1].name()[-1])+1
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
            "x": int(check_format.x()),
            "y": int(check_format.y()),
            "r": int(check_format.r()),
            "t": int(check_format.t()),
            "pixel_aspect": float(check_format.pixelAspect())
        }
        crnt_fmt_str = make_format_string(**crnt_fmt_kargs)
        log.info("crnt_fmt_str: {}".format(crnt_fmt_str))

    new_fmt_kargs = {
        "width": int(width),
        "height": int(height),
        "x": int(x),
        "y": int(y),
        "r": int(r),
        "t": int(t),
        "pixel_aspect": float(pixel_aspect),
        "project_name": format_name
    }

    new_fmt_str = make_format_string(**new_fmt_kargs)
    log.info("new_fmt_str: {}".format(new_fmt_str))

    if new_fmt_str not in crnt_fmt_str:
        make_format(frm_str=new_fmt_str,
                    project_name=new_fmt_kargs["project_name"])

        log.info("Format is set")


def make_format_string(**args):
    format_str = (
        "{width} "
        "{height} "
        "{x} "
        "{y} "
        "{r} "
        "{t} "
        "{pixel_aspect:.2f}".format(**args)
    )
    return format_str


def make_format(**args):
    log.info("Format does't exist, will create: \n{}".format(args))
    nuke.addFormat("{frm_str} "
                   "{project_name}".format(**args))
    nuke.root()["format"].setValue("{project_name}".format(**args))


# TODO: bellow functions are wip and needs to be check where they are used
# ------------------------------------


def update_frame_range(start, end, root=None):
    """Set Nuke script start and end frame range

    Args:
        start (float, int): start frame
        end (float, int): end frame
        root (object, Optional): root object from nuke's script

    Returns:
        None

    """

    knobs = {
        "first_frame": start,
        "last_frame": end
    }

    with avalon.nuke.viewer_update_and_undo_stop():
        for key, value in knobs.items():
            if root:
                root[key].setValue(value)
            else:
                nuke.root()[key].setValue(value)


def get_additional_data(container):
    """Get Nuke's related data for the container

    Args:
        container(dict): the container found by the ls() function

    Returns:
        dict
    """

    node = container["_tool"]
    tile_color = node['tile_color'].value()
    if tile_color is None:
        return {}

    hex = '%08x' % tile_color
    rgba = [
        float(int(hex[0:2], 16)) / 255.0,
        float(int(hex[2:4], 16)) / 255.0,
        float(int(hex[4:6], 16)) / 255.0
    ]

    return {"color": QtGui.QColor().fromRgbF(rgba[0], rgba[1], rgba[2])}
