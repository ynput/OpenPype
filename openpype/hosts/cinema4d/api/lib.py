# @carver library of functions we usually call helpers
from os import name
import c4d
import contextlib
from collections import OrderedDict
import random
from pathlib import PurePosixPath 

from .c4d_lib import ObjectAttrs, ObjectPath

from six import string_types

def get_main_window():
    return None


@contextlib.contextmanager
def maintained_selection(doc=None):
    """Maintain selection during context

    Example:
        >>> scene = cmds.file(new=True, force=True)
        >>> node = cmds.createNode("transform", name="Test")
        >>> cmds.select("persp")
        >>> with maintained_selection():
        ...     cmds.select("Test", replace=True)
        >>> "Test" in cmds.ls(selection=True)
        False

    """
    if not doc:
        doc = c4d.documents.GetActiveDocument()
    previous_selection = doc.GetSelection()
    try:
        yield
    finally:
        if previous_selection:
            first = True
            for select in previous_selection:
                if first:
                    flag = c4d.SELECTION_NEW
                    first = False
                else:
                    flag = c4d.SELECTION_ADD
                doc.SetSelection(select, flag)
        else:
            for select in doc.GetSelection():
                doc.SetSelection(select, c4d.SELECTION_SUB)

###### Method for addressing objects in C4D


def read(node):
    """Return user-defined attributes from `node`"""

    data = dict(**ObjectAttrs(node))
    '''
    for attr in cmds.listAttr(node, userDefined=True) or list():
        try:
            value = cmds.getAttr(node + "." + attr, asString=True)

        except RuntimeError:
            # For Message type attribute or others that have connections,
            # take source node name as value.
            source = cmds.listConnections(node + "." + attr,
                                          source=True,
                                          destination=False)
            source = cmds.ls(source, long=True) or [None]
            value = source[0]

        except ValueError:
            # Some attributes cannot be read directly,
            # such as mesh and color attributes. These
            # are considered non-essential to this
            # particular publishing pipeline.
            value = None

        data[attr] = value

    '''
    return data

def create_selection(objs, name, doc=None):
    if not doc:
        if len(objs) > 0:
            doc = objs[0].GetDocument()
        else:
            doc = c4d.documents.GetActiveDocument()
    
    selection = c4d.BaseObject(c4d.Oselection)
    selection.SetName(name)
    doc.InsertObject(selection)
    inexcludedata = c4d.InExcludeData()
    for obj in objs:
        inexcludedata.InsertObject(obj, 1)
    ObjectAttrs(selection)["SELECTIONOBJECT_LIST"] = inexcludedata

    return selection

def add_update_layer( name, doc=None, layer_data={}):
    if not doc:
        doc = c4d.documents.GetActiveDocument()


    layer_root = doc.GetLayerObjectRoot()
    layer = layer_root.GetDown()
    update_layer = None
    for l in recurse_hierarchy(layer):
        if l.GetName() == name:
            update_layer = l
            break

    if not update_layer:
        update_layer = c4d.documents.LayerObject()
        update_layer.SetName(name)
        update_layer.InsertUnder(layer_root)

    if not layer_data and not update_layer:
        layer_data = {
                        "solo":False,
                        "view":True,
                        "render":True,
                        "manager":True,
                        "locked":False,
                        "generators":True,
                        "expressions":True,
                        "animation":True,
                        "color":c4d.Vector(random.random(),random.random(),random.random()),
                        "xref":True
                    }

    if layer_data and update_layer:
        old_data = update_layer.GetLayerData(doc, rawdata=True)
        print(type(layer_data))
        old_data.update(layer_data)
        layer_data = old_data

    if layer_data: 
        update_layer.SetLayerData(doc, layer_data)

    return update_layer

def add_object_to_layer(layer_name, obj):
    layer = add_update_layer(layer_name, doc=obj.GetDocument())
    obj[c4d.ID_LAYER_LINK] = layer
    return obj[c4d.ID_LAYER_LINK] == layer
### playing around with different options for handling objects

def recurse_hierarchy(obj):
    while obj:
        yield obj
        for x in recurse_hierarchy(obj.GetDown()):
            yield x
        obj = obj.GetNext()


def serialize_c4d_data(data, doc=None):
    if not doc:
        doc = c4d.documents.GetActiveDocument()

    data_type = type(data)

    if data_type == c4d.Vector:
        return [data.x, data.y, data.z]
    elif data_type == c4d.Matrix:
        return [
            [data.off.x, data.off.y, data.off.z],
            [data.v1.x, data.v1.y, data.v1.z],
            [data.v2.x, data.v2.y, data.v2.z],
            [data.v3.x, data.v3.y, data.v3.z]
        ]
    elif isinstance(data, c4d.BaseObject):
        return f"BaseObject-{data.GetType()}:" + get_obj_absolute_path(data).as_posix()
    elif data_type == c4d.BaseMaterial:
        return "BaseMaterial:" + data.GetName()
    elif data_type == c4d.InExcludeData:
        data_list = list()
        for idx in range(data.GetObjectCount()):
            data_list.append(serialize_c4d_data(data.ObjectFromIndex(doc, idx)))
        return data_list
    elif data_type in [str, float, int] or data is None:
        return data
    else:
        raise TypeError(f"Unsupported Data Type {data_type.__name__}")

def deserialize_c4d_data(data, doc=None, objs=None):

    if not doc:
        doc = c4d.documents.GetActiveDocument()

    if not objs:
        objs = [x for x in recurse_hierarchy(doc.GetFirstObject())]

    def _extract_baseobject(item):
        item = item.split(":")[1]

        obj = search_obj_path(item)
        return obj

    def _extract_basematerial(item):
        item = item.replace("BaseMaterial:", "")
        mat = doc.GetFirstMaterial()
        while mat:
            if mat.GetName() == item:
                return mat
            mat = mat.GetNext()
        return None


    data_type = type(data)

    if data_type == list:
        if len(data) == 3 and type(data[0]) == float:
            return c4d.Vector(*data)
        elif len(data) == 4 and type(data[0]) == list and type(data[0][0]) == float:
            return c4d.Matrix(
                c4d.Vector(*data[0]),
                c4d.Vector(*data[1]),
                c4d.Vector(*data[2]),
                c4d.Vector(*data[3])
                )
        else:
            data_inexclude = c4d.InExcludeData()
            for item in data:
                obj = _extract_baseobject(item)
                data_inexclude.InsertObject(obj)
                        
            return data_inexclude
    elif data_type == str and data.startswith("BaseObject-"):
        return _extract_baseobject(data)

    elif data_type == str and data.starswith("BaseMaterial:"):
        return _extract_basematerial(data)
    
    else:
        return data

def get_baseobject_by_name(name, doc=None, objs=None):
    if not doc:
        doc=c4d.documents.GetActiveDocument()

    if not objs:
        objs = [x for x in recurse_hierarchy(doc.GetFirstObject())]

    for obj in objs:
        if obj.GetName() == name:
            return obj
    
    return None

def get_obj_paths(root, prefix="/"):

    while root:
        path = ObjectPath(prefix, root.GetName())
        yield path, root

        for x, y  in get_obj_paths(root.GetDown(), prefix=path):
            yield x, y
        root = root.GetNext()

def search_obj_path(path, doc=None, root=None):
    if not doc:
        doc = c4d.documents.GetActiveDocument()
    if not root:
        root = doc.GetFirstObject()
    
    for p, obj in get_obj_paths(root):
        if p.match(path):
            return obj

def get_obj_absolute_path(obj):
    path = []

    while obj:
        path.append(obj.GetName())
        obj = obj.GetUp()
    path.reverse()
    return ObjectPath("/", *path)

    
def collect_animation_data(fps=False, doc=None):
    """Get the basic animation data

    Returns:
        OrderedDict

    """
    if not doc:
        doc = c4d.documents.GetActiveDocument()

    # get scene values as defaults
    start = doc.GetMinTime().GetFrame(doc.GetFps())
    end = doc.GetMaxTime().GetFrame(doc.GetFps())

    # build attributes
    data = OrderedDict()
    data["frameStart"] = start
    data["frameEnd"] = end
    data["handleStart"] = 0
    data["handleEnd"] = 0
    data["step"] = 1.0

    if fps:
        data["fps"] = doc.GetFps()

    return data



def imprint(op, data, doc=None, objs=None):
    """Write `data` to `op` as userDefined attributes

    Arguments:
        obj_name (str): Long name of obj_name
        data (dict): Dictionary of key/value pairs

    Example:
        >>> from maya import cmds
        >>> def compute():
        ...   return 6
        ...
        >>> cube, generator = cmds.polyCube()
        >>> imprint(cube, {
        ...   "regularString": "myFamily",
        ...   "computedValue": lambda: compute()
        ... })
        ...
        >>> cmds.getAttr(cube + ".computedValue")
        6

    """
    #op = get_baseobject_by_name(obj_name, doc=doc, objs=objs)
    if op:
        op_attrs = ObjectAttrs(op)
        for key, value in data.items():

            if callable(value):
                # Support values evaluated at imprint
                value = value()

            if key in op_attrs.keys():
                op_attrs[key] = value
            else:
                op_attrs.add_attr(key, value)
