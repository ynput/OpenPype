import sys
from collections import OrderedDict
from pprint import pprint
from avalon.vendor.Qt import QtGui
import avalon.nuke
import pype.api as pype
import nuke

log = pype.Logger.getLogger(__name__, "nuke")
self = sys.modules[__name__]
self._project = None


def format_anatomy(data):
    from .templates import (
        get_anatomy
    )
    file = script_name()

    anatomy = get_anatomy()
    padding = anatomy.render.padding

    data.update({
        "hierarchy": pype.get_hiearchy(),
        "frame": "#"*padding,
        "VERSION": pype.get_version_from_workfile(file)
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
    try:
        anatomy_filled = format_anatomy({
            "subset": data["avalon"]["subset"],
            "asset": data["avalon"]["asset"],
            "task": pype.get_task(),
            "family": data["avalon"]["family"],
            "project": {"name": pype.get_project_name(),
                        "code": pype.get_project_code()},
            "representation": nuke_dataflow_writes.file_type,
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
    except:
        return None
    return data

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
