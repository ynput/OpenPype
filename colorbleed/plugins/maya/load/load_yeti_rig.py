import colorbleed.maya.plugin


class YetiRigLoader(colorbleed.maya.plugin.ReferenceLoader):

    families = ["colorbleed.yetiRig"]
    representations = ["ma"]

    label = "Load Yeti Rig"
    order = -9
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name=None, namespace=None, data=None):

        import maya.cmds as cmds
        from avalon import maya

        with maya.maintained_selection():
            nodes = cmds.file(self.fname,
                              namespace=namespace,
                              reference=True,
                              returnNewNodes=True,
                              groupReference=True,
                              groupName="{}:{}".format(namespace, name))

        self[:] = nodes

        self._post_process(name, name, context, data)

        return nodes

    def _post_process(self, name, namespace, context, data):

        import os
        import json

        import maya.cmds as cmds

        import avalon.maya.lib as lib

        # Get json data
        fname, ext = os.path.splitext(self.fname)
        data_file = "{}.rigsettings".format(fname)

        with open(data_file, "r") as fp:
            rigsettings = json.load(fp)

        # Get content from input_SET
        input_set = [i for i in self if "input_SET" in i]
        assert len(input_set) == 1, "Could not find input_SET!"
        members = cmds.ls(cmds.sets(input_set[0], query=True), long=True)

        for input in rigsettings["inputs"]:

            # Find input / output mesh
            # Ensure the mesh is not it's self
            plug_id_matches = lib.lsattr("cbId", input["plugID"]) or []
            plug_mesh = [i for i in plug_id_matches if i not in members]

            # Ensure connection goes to the correct mesh (might be duplicates)
            socket_id_matches = lib.lsattr("cbId", input["socketID"]) or []
            socket_mesh = [i for i in socket_id_matches if i in members]
            if len(plug_mesh) == 0:
                return

            # Connect meshes, list of attributes to connect
            socket_attr, plug_attr = input["connections"]
            _plug_attr = "{}.{}".format(plug_mesh[0], plug_attr)
            _socket_attr = "{}.{}".format(socket_mesh[0], socket_attr)
            try:
                cmds.connectAttr(_plug_attr, _socket_attr)
            except Exception as e:
                self.log.wanring(e)
                continue

        return
