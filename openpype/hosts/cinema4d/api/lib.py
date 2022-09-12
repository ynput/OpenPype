import c4d
import re
import math
from six import string_types
import contextlib
import random
from collections import OrderedDict
from openpype.pipeline import legacy_io
from openpype.client import (
    get_project,
    get_asset_by_name,
    get_versions,
    get_last_versions,
    get_representations,
)
from openpype.api import (
    Logger,
    BuildWorkfile,
    get_version_from_path,
    get_workdir_data,
    get_asset,
    get_current_project_settings,
)
'''
TODO:
Add other objects types to ObjectAttrs
Add shader nodes to attrs + path
'''

class ObjectAttrs:
    '''
    Manages data from baseobjects in c4d. Built in object data
    uses the built in DESC_IDENT. e.g. to get a name natively in 
    c4d you would use op[c4d.ID_BASELIST_NAME] with this class
    you would user ObjectAttrs(op)["ID_BASELIST_NAME"].

    More importantly userdata can be accessed by the label of the 
    userdata e.g. userdata witha label of "test_strength" can be accessed
    ObjectAttrs(op)["test_strength"]

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

    def reset_attrs(self):
        self.user_data = dict()
        self.object_data = dict()
        self.tag_data = dict()
        self.get_attrs()

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
            #raise AttributeError
            self.add_attr(key, value)
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
        
        for key in self.user_data.keys():
            yield key

        for key in self.tag_data.keys():
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
        self.reset_attrs()

    def remove_attr(self, key):
        if key in self.user_data.keys():
            result = self.op.RemoveUserData(self.user_data[key]["access_id"])
            if result:
                self.user_data.pop(key)
                self.op.Message(c4d.MSG_CHANGE)
                c4d.EventAdd()
                self.reset_attrs()
            return result
        else:
            return False

    def __repr__(self):
        return f'<ObjectAttrs: {self.op.GetName()}>'

class ObjectPath():
    """
    Representing the c4d hiearchy in a namespace/pathlike manner.
    This is intended to make serialization of hierarchy and assets easier,
    as well as using naming patterns for searching

    Each unique space in c4d can kind of be thought like a drive in a file system with
    the main exception that you can stack "drives" in the hierarchy for example if there is an 
    xpresso tag on an object and you you want to address a node in the node graph it could look like
    :obj:/first_obj/child_obj:tag:/xpresso_tag:node:/xgroup/object_node
    """

    def __init__(self, *parts, doc=None, obj=None):
        self.sep = "/"
        self._id = ":{space}:"
        self.spaces = ["obj", "tag", "node", "mat"]
        self.parts = []
        self.roots = []
        self.doc = doc
        self._obj = obj
        self._attrs = None
        if self._obj:
            self.from_obj(self._obj)
        else:
            self._initialize_path(*parts)


    def _initialize_path(self, *parts):
        p = []
        for part in parts:
            for subpart in str(part).split(self.sep):
                contains_root = False
                for space in [self._id.format(space=x) for x in self.spaces]:
                    if len(subpart.split(space)) > 1:
                        contains_root = True
                        break
                if contains_root:
                    part_a = subpart.split(space)[0]
                    part_b = subpart.split(space)[1]
                    if part_a:
                        p.append(part_a)
                    if len(p):
                        self.parts.append(p)
                    self.roots.append(space)
                    p = []
                    if part_b:
                        p.append(part_b)
                elif subpart:
                    p.append(subpart)
        if not len(p):
            self.parts.append([""])
        else:
            self.parts.append(p)
    def _get_obj_parts(self, obj):
        parts = []
        while obj:
            parts.append(obj.GetName())
            obj = obj.GetUp()
        parts.reverse()
        return parts

    def _get_obj_root(self, obj):
        if isinstance(obj, c4d.BaseMaterial):
            space = "mat"
        elif isinstance(obj, c4d.BaseTag):
            space = "tag"
        elif isinstance(obj, c4d.modules.graphview.GvNode):
            space = "node"
        else:
            space = "obj"

        return self._id.format(space=space)

    def from_obj(self, obj):

        self.parts = list()
        self.roots = list()

        if self._get_obj_root(obj) ==  self._id.format(space="node"):
            self.roots = [self._get_obj_root(obj)] + self.roots
            self.parts = [self._get_obj_parts(obj)] + self.parts
            obj = obj.GetMain().GetOwner()

        if self._get_obj_root(obj) ==  self._id.format(space="tag"):
            self.roots = [self._get_obj_root(obj)] + self.roots
            self.parts = [self._get_obj_parts(obj)] + self.parts
            obj = obj.GetObject()

        if self._get_obj_root(obj) ==  self._id.format(space="mat"):
            self.roots = [self._get_obj_root(obj)] + self.roots
            self.parts = [self._get_obj_parts(obj)] + self.parts

        if self._get_obj_root(obj) ==  self._id.format(space="obj"):
            self.roots = [self._get_obj_root(obj)] + self.roots
            self.parts = [self._get_obj_parts(obj)] + self.parts

        return self

    @property
    def name(self):
        name = None
        if len(self.parts):
            if len(self.parts[-1]):
                name = self.parts[-1][-1]
        return name or ""

    @property
    def parent(self):
        if len(self.parts[-1])>0:
            temp_parts = self.parts[:-1]
            temp_parts.append(self.parts[-1][:-1])
            new_path = self.__class__()
            new_path.doc = self.doc
            new_path.parts = temp_parts
            new_path.roots = self.roots
            return new_path
        else:
            temp_roots = self.roots[:-1]
            new_path = self.__class__()
            new_path.doc = self.doc
            new_path.parts = self.parts
            new_path.roots = temp_roots
            return new_path

    @property
    def attrs(self):
        if self.exists():
            if not self._attrs:
                self._attrs = ObjectAttrs(self.obj)
            return self._attrs
        raise AttributeError("Object Does Not Exist")
    def __repr__(self):
        return "<%s(%s)>" % (self.__class__.__name__, self.__str__())

    def __str__(self):
        if len(self.roots)<len(self.parts):
            temp_roots = [""] + self.roots
        elif len(self.roots) == 0:
            temp_roots = [""]
        else:
            temp_roots = self.roots

        path_str = ""
        for idx, root in enumerate(temp_roots):

            if root:
                path_str += root + self.sep

            path_str += self.sep.join(self.parts[idx])

        return path_str
    '''
    def __eq__(self, other):
        return hash(self) == hash(other)

    def __hash__(self):
        if self.exists():
            return hash(repr(self.obj))
        else:
            return hash(str(self))
    '''
    def re_match(self, pattern, full=True):
        if full:
            return re.fullmatch(pattern,str(self))
        else:
            return re.match(pattern,str(self))

    def _get_obj(self, root, parts, parent=None):

        if root == self._id.format(space="obj"):
            if isinstance(parent, c4d.documents.BaseDocument):
                root_obj = parent.GetFirstObject()
            elif isinstance(parent, c4d.BaseObject):
                root_obj = parent.GetDown()
            else:
                return None

            while len(parts):
                obj = None
                part = parts.pop(0)
                for sib in get_siblings(root_obj):
                    if sib.GetName() == part:
                        obj = sib
                        continue
                if not obj:
                    return None
                else:
                    root_obj = obj.GetDown()
            return obj

    @property
    def obj(self):
        if self._obj:
            return self._obj
        if not self.doc:
            parent = c4d.documents.GetActiveDocument()
        else:
            parent = self.doc

        temp_parts = self.parts
        temp_roots = self.roots

        while len(temp_parts):
            root = temp_roots.pop(0)
            parts = temp_parts.pop(0)
            parent = self._get_obj(root, parts, parent)
            if not parent:
                return None
        self._obj = parent
        return parent

    def exists(self):
        return self.obj != None

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

def read(node):
    """Return user-defined attributes from `node`"""

    data = dict(**ObjectAttrs(node))

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
    for obj_path in walk_hierarchy(layer):
        if obj_path.obj.GetName() == name:
            update_layer = obj_path.obj
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
        return str(ObjectPath(obj=data))
    elif data_type == c4d.BaseMaterial:
        return str(ObjectPath(obj=data))
    elif data_type == c4d.InExcludeData:
        data_list = list()
        for idx in range(data.GetObjectCount()):
            data_list.append(serialize_c4d_data(data.ObjectFromIndex(doc, idx)))
        return data_list
    elif data_type in [str, float, int] or data is None:
        return data
    elif isinstance(data, ObjectPath):
        return serialize_c4d_data(data.obj)
    elif isinstance(data, ObjectAttrs):
        return serialize_c4d_data(data.op)
    else:
        raise TypeError(f"Unsupported Data Type {data_type.__name__}")

def deserialize_c4d_data(data):

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
                op = ObjectPath(item)
                if op.exists():
                    data_inexclude.InsertObject(op.obj)
                        
            return data_inexclude
    elif data_type == str and data.startswith(":obj:"):
        return ObjectPath(data).obj
    elif data_type == str and data.startswith(":mat:"):
        return ObjectPath(data).obj
    elif data_type == str and data.startswith(":node:"):
        return ObjectPath(data).obj
    elif data_type == str and data.startswith(":tag:"):
        return ObjectPath(data).obj   
    else:
        return data


def get_siblings(obj):
    while obj:
        start_obj = obj
        obj = obj.GetPred()
    while start_obj:
        yield start_obj
        start_obj = start_obj.GetNext()

def walk_hierarchy(root):
    while root:
        yield ObjectPath(obj=root)
        for obj in walk_hierarchy(root.GetDown()):
            yield obj
        root = root.GetNext()

def visible_in_viewport(obj):
    if obj[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] == 1:
        return False
    if obj[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] == 2:
        temp_obj = obj.GetUp()
        while temp_obj:
            if temp_obj[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] == 1:
                return False
            temp_obj = temp_obj.GetUp()
    if obj[c4d.ID_LAYER_LINK]:
        if not obj[c4d.ID_LAYER_LINK].GetLayerData(obj.GetDocument()).get("view"):
            return False

    return True

def visible_in_render(obj):
    if obj[c4d.ID_BASEOBJECT_VISIBILITY_RENDER] == 1:
        return False
    if obj[c4d.ID_BASEOBJECT_VISIBILITY_RENDER] == 2:
        temp_obj = obj.GetUp()
        while temp_obj:
            if temp_obj[c4d.ID_BASEOBJECT_VISIBILITY_RENDER] == 1:
                return False
            temp_obj = temp_obj.GetUp()
    if obj[c4d.ID_LAYER_LINK]:
        if not obj[c4d.ID_LAYER_LINK].GetLayerData(obj.GetDocument()).get("render"):
            return False

    return True




'''
Vaguely based on the maya ls, mainly I just wanted a unified way to iterate over
all the objects in a project file and find what I am looking for without having
to write bespoke functions every single time.
'''
def ls(
    search_list=None,
    name="",
    exact_name=False,
    absolute_path=False,
    regex_pattern=False,
    selected=False,
    include_children=False,
    as_string=False,
    visible=False,
    rendered=False,
    _type=None,
    exact_type=None,
    tags=False,
    materials=False,
    objects=True,
    layers=False,
    nodes=False,
    doc=None,
    attrs = {}
    ):


    if not doc:
        doc = c4d.documents.GetActiveDocument()

    def _is_valid(op_path):

        if absolute_path:
            if str(op_path) != name:
                return None
        else:
            if regex_pattern:
                _name = name
            elif exact_name:
                _name = ".*/"+name  
            else:
                _name = ".*"+name+"(?!.*/).*"

            match = op_path.re_match(_name)

            if not match:
                return False

        if _type and not isinstance(op_path.obj, _type):
            return False
        if not isinstance(op_path.obj, c4d.BaseMaterial):
            if visible and not visible_in_viewport(op_path.obj):
                return False
            if rendered and not visible_in_render(op_path.obj):
                return False
        if exact_type and  type(op_path.obj) != exact_type:
            return False
        if selected and op_path.obj not in doc.GetSelection():
            return False

        if attrs:
            if op_path.exists():
                for key, value in attrs.items():
                    if not op_path.attrs.get(key) or op_path.attrs.get(key) != value:
                        return False
        return True

    items = []

    if search_list:
        if not isinstance(search_list, list):
            if isinstance(search_list, c4d.InExcludeData):
                inex_data = search_list
                search_list = []
                for idx in range(inex_data.GetObjectCount()):
                    search_list.append(inex_data.ObjectFromIndex(idx))
    else:
        search_list = []
        if objects or nodes or tags:
            search_list += [x for x in walk_hierarchy(doc.GetFirstObject())]
        if materials:
            search_list += [x for x in walk_hierarchy(doc.GetFirstMaterial())]
    
    for op_path in search_list:

        if objects or materials:

            if _is_valid(op_path):
                if as_string:
                    items.append(str(op_path))
                else:
                    items.append(op_path)

        if tags or nodes:
            for op_path in walk_hierarchy(op_path.obj.GetFirstTag()):
                if tags:

                    if _is_valid(op_path):
                        if as_string:
                            items.append(str(op_path))
                        else:
                            items.append(op_path)
                if nodes and isinstance(op_path.obj, c4d.modules.graphview.XPressoTag):
                    for op_path in walk_hierarchy(op_path.obj.GetNodeMaster().GetRoot()):
                        if _is_valid(op_path):
                            if as_string:
                                items.append(str(op_path))
                            else:
                                items.append(op_path)


    return items


def get_doc_session(doc=None):
    if not doc:
        doc = c4d.documents.GetActiveDocument()

    session_obj_paths = ls(name="__session__")
    if len(session_obj_paths) == 0:
        return {}
    
    session_op = session_obj_paths[0]

    return dict(**session_op.attrs)

def update_global_session_from_doc(doc=None):
    if not doc:
        doc = c4d.documents.GetActiveDocument()
    doc_session = get_doc_session(doc)
    for key, value in legacy_io.Session.items():
        if doc_session.get(key):
            legacy_io.Session[key] = doc_session[key]

def set_doc_session(doc=None, session=None):
    if not session:
        session = legacy_io.Session
    if not doc:
        doc = c4d.documents.GetActiveDocument()

    session_obj_paths = ls(name="__session__")
    if len(session_obj_paths) == 0:
        null_obj = c4d.BaseObject(c4d.Onull)
        null_obj.SetName("__session__")
        doc.InsertObject(null_obj)
        add_update_layer('__session__', doc, {"locked":True, "view":False, "render":False, "manager":False})
        add_object_to_layer("__session__", null_obj)
        c4d.EventAdd()    
        obj_attrs = ObjectAttrs(null_obj)
    else:
        obj_attrs = session_obj_paths[0].attrs

    obj_attrs["AVALON_PROJECT"] = session["AVALON_PROJECT"]
    obj_attrs["AVALON_ASSET"] = session["AVALON_ASSET"]
    obj_attrs["AVALON_TASK"] = session["AVALON_TASK"]


class WorkfileSettings(object):


    def __init__(self,  doc=None, **kwargs):
        if not doc:
            self.doc = c4d.documents.GetActiveDocument()
        project_doc = kwargs.get("project")
        if project_doc is None:
            project_name = legacy_io.active_project()
            project_doc = get_project(project_name)

        self._asset = (
            kwargs.get("asset_name")
            or legacy_io.Session["AVALON_ASSET"]
        )
        self._asset_entity = get_asset(self._asset)


        self.data = kwargs

    def set_frame_range_handles(self):
        data = self._asset_entity["data"]
        #log.debug("__ asset data: `{}`".format(data))

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
            #log.warning(msg)
            return

        # get handles values
        handle_start = int(data["handleStart"])
        handle_end = int(data["handleEnd"])

        f_fps = float(data["fps"])
        i_fps = int(math.ceil(data["fps"]))
        frame_start = int(data["frameStart"]) - handle_start
        frame_end = int(data["frameEnd"]) + handle_end
        bt_frame_start = c4d.BaseTime(frame_start, i_fps)
        bt_frame_end = c4d.BaseTime(frame_end, i_fps)
        #set document fps
        self.doc.SetFps(i_fps)
        # set document frame range
        self.doc.SetMinTime(bt_frame_start)
        self.doc.SetMaxTime(bt_frame_end)
        self.doc.SetLoopMinTime(bt_frame_start)
        self.doc.SetLoopMaxTime(bt_frame_end)

        
        rd = self.doc.GetFirstRenderData()

        while rd:
            # set render fps
            rd[c4d.RDATA_FRAMERATE] = f_fps
            # set render frame range
            rd[c4d.RDATA_FRAMEFROM] = bt_frame_start
            rd[c4d.RDATA_FRAMETO] = bt_frame_end
            rd = rd.GetNext()

        c4d.EventAdd()

    def set_colorspace_viewport(self):
        pass
    
    def set_colorspace_redshift(self):
        pass

    def set_colorspace_arnold(self):
        pass

    def set_resolution(self):
        data = self._asset_entity["data"]
        #log.debug("__ asset data: `{}`".format(data))

        missing_cols = []
        check_cols = ["resolutionWidth", "resolutionHeight"]

        for col in check_cols:
            if col not in data:
                missing_cols.append(col)

        if len(missing_cols) > 0:
            missing = ", ".join(missing_cols)
            msg = "'{}' are not set for asset '{}'!".format(
                missing, self._asset)
            #log.warning(msg)
            return
        rd = self.doc.GetFirstRenderData()

        while rd:
            rd[c4d.RDATA_XRES] = int(data["resolutionWidth"])
            rd[c4d.RDATA_YRES] = int(data["resolutionHeight"])
            rd = rd.GetNext()
        c4d.EventAdd()
    def set_all_colorspace(self):
        pass