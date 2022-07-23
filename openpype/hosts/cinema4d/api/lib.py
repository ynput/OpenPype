# @carver library of functions we usually call helpers
import c4d

def get_main_window():
    return None


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
        self.user_data = dict()
        self.object_data = dict()
        self.tag_data = dict()
        self.get_attrs()

    def get_attrs(self):
        desc = self.op.GetDescription(c4d.DESCFLAGS_DESC_NONE)

        for bc, paramid, groupid in desc:
            if bc[c4d.DESC_IDENT]:
                try:
                    self.object_data[bc[c4d.DESC_IDENT]] = {"value":self.op[paramid[0].id], "access_id":paramid[0].id}
                except AttributeError:
                    if bc[c4d.DESC_IDENT] == "ID_USERDATA":
                        for id, ud_bc in self.op.GetUserDataContainer():
                            self.user_data[ud_bc.GetString(c4d.DESC_NAME)] = {
                                "value":self.op[c4d.ID_USERDATA, id[1].id],
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
            self.op[c4d.ID_USERDATA, self.user_data[key]["access_id"]] = value
            self.user_data[key]["value"] = value
        else:
            raise AttributeError
        self.doc.EndUndo()
        if self.auto_update():
            c4d.EventAdd()

    def __iter__(self):
        for key, values in self.object_data.items():
            yield key, values["value"]
        
        for key, values in self.user_data.items():
            yield key, values["value"]

        for key, values in self.tag_data.items():
            yield key, values["value"]

    def get(self, key, default=None):
        try:
            self.__getitem__(key)
        except KeyError:
            return default
            
    def __repr__(self):
        return f'<ObjectAttrs: {self.op.GetName()}>'