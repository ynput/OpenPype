# @carver library of functions we usually call helpers
from os import name
import c4d
import contextlib
from collections import OrderedDict
import random
from pathlib import PurePosixPath as ObjectPath

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


class ObjectAttrs:
    '''
    Manages data from baseobjects in c4d. Built in object data
    uses the built in DESC_IDENT. e.g. to get a name natively in 
    c4d you would use op[c4d.ID_BASELIST_NAME] with this class
    you would user ObjectAttrs(op)["ID_BASELIST_NAME"].

    More importantly userdata can be accessed by the label of the 
    userdata e.g. userdata witha label of "test_strength" can be accessed
    ObjectAttrs(op)["test_strength"]

    TODO: create a way to consistently get data from tags possibly putting tags in a namespace
    '''
    def __init__(self, op, tags=False, auto_update=True):
        self.op = op
        self.doc = op.GetDocument()
        self.auto_update=auto_update
        self.user_data = dict()
        self.object_data = dict()
        self.tag_data = dict()
        self.get_attrs()

    def get_attrs(self):
        desc = self.op.GetDescription(c4d.DESCFLAGS_DESC_NONE)

        for bc, paramid, groupid in desc:
            if isinstance(bc[c4d.DESC_IDENT], str):
                try:
                    self.object_data[bc[c4d.DESC_IDENT]] = {"value":self.op[paramid[0].id], "access_id":paramid[0].id}
                except AttributeError:
                    if bc[c4d.DESC_IDENT] == "ID_USERDATA":
                        for id, ud_bc in self.op.GetUserDataContainer():
                            if ud_bc[c4d.DESC_CUSTOMGUI] == c4d.CUSTOMGUI_CYCLE:
                                choices = ud_bc[c4d.DESC_CYCLE]
                                value = choices.GetString(self.op[id[0].id, id[1].id])
                            else: 
                                value = self.op[c4d.ID_USERDATA, id[1].id]
                            self.user_data[ud_bc.GetString(c4d.DESC_NAME)] = {
                                "value":value,
                                "access_id":id[1].id
                            }

    def __getitem__(self, key):
        self.get_attrs()
        if key in self.object_data.keys():
            return self.object_data[key]["value"]

        elif key in self.user_data.keys():
            return self.user_data[key]["value"]

        else:
            raise KeyError

    def __setitem__(self, key, value):
        self.doc.StartUndo()
        self.doc.AddUndo(c4d.UNDOTYPE_CHANGE_SMALL, self.op)

        if key in self.object_data.keys():
            self.op[self.object_data[key]["access_id"]] = value
            self.object_data[key]["value"] = value

        elif key in self.user_data.keys():
            desc, ud_bc = self.op.GetUserDataContainer()[self.user_data[key]["access_id"]-1]
            if ud_bc[c4d.DESC_CUSTOMGUI] == c4d.CUSTOMGUI_CYCLE:
                choices = ud_bc[c4d.DESC_CYCLE]
                for choice in choices:
                    if choice[1] == value:
                        new_value = choice[0]
                        break
            else:
                new_value = value

            self.op[c4d.ID_USERDATA, self.user_data[key]["access_id"]] = new_value
            self.user_data[key]["value"] = value
        else:
            raise AttributeError
        self.doc.EndUndo()
        if self.auto_update:
            c4d.EventAdd()

    def __iter__(self):
        for key, values in self.object_data.items():
            yield key, values["value"]
        
        for key, values in self.user_data.items():
            yield key, values["value"]

        for key, values in self.tag_data.items():
            yield key, values["value"]

    def keys(self):
        for key in self.object_data.keys():
            yield key
        
        for key, values in self.user_data.keys():
            yield key

        for key, values in self.tag_data.keys():
            yield key

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def add_attr(self, key, value, exists_ok=False):
        if key in self.user_data.keys():
            if exists_ok:
                self.__setitem__[key] = value
                return
            else:
                raise AttributeError("Attribute already exists")  
        if isinstance(value, bool):
            bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_BOOL)
            bc[c4d.DESC_NAME] = key
        elif isinstance(value, string_types):
            bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_STRING)
            bc[c4d.DESC_NAME] = key
        elif isinstance(value, int):
            bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_LONG)
            bc[c4d.DESC_NAME] = key
        elif isinstance(value, float):
            bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_REAL)
            bc[c4d.DESC_NAME] = key
        elif isinstance(value, c4d.BaseList2D):
            bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_BASELISTLINK)
            bc[c4d.DESC_CUSTOMGUI] = c4d.CUSTOMGUI_LINKBOX
            bc[c4d.DESC_NAME] = key
        elif isinstance(value, (list, tuple)):
            if len(value) > 0 and isinstance(value[0], c4d.BaseList2D):
                bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_BASELISTLINK)
                bc[c4d.DESC_CUSTOMGUI] = c4d.CUSTOMGUI_INEXCLUDE_LIST
                bc[c4d.DESC_NAME] = key
                new_value = c4d.InExcludeData()
                for v in value:
                    new_value.InsertObject(v, 1)
                value = new_value
            else:
                bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_LONG)
                bc[c4d.DESC_NAME] = key
                bc[c4d.DESC_CUSTOMGUI] = c4d.CUSTOMGUI_CYCLE

                choices = c4d.BaseContainer()
                for idx, choice in enumerate(value):
                    choices.SetString(idx, str(choice))

                bc.SetContainer(c4d.DESC_CYCLE, choices)
                value=0
        else:
            raise TypeError("Unsupported type: %r" % type(value))

        desc = self.op.AddUserData(bc)
        self.op[desc[0].id, desc[1].id] = value

        c4d.EventAdd()

    def remove_attr(self, key):
        if key in self.user_data.keys():
            result = self.op.RemoveUserData(self.user_data[key]["access_id"])
            if result:
                c4d.EventAdd()
            return result
        else:
            return False

    def __repr__(self):
        return f'<ObjectAttrs: {self.op.GetName()}>'


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
