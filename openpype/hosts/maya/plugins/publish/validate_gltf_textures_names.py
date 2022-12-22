from maya import cmds

import pyblish.api
import openpype.hosts.maya.api.action
from openpype.pipeline.publish import ValidateContentsOrder


class ValidateGLTFTexturesNames(pyblish.api.InstancePlugin):
    """
    Validate if the asset uses StingrayPBS material before conversion
    of the GLSL Shader
    Validate if the names of GLTF Textures follow
    the packed ORM/ORMS standard.

    The texture naming conventions follows the UE5-style-guides:
    https://github.com/Allar/ue5-style-guide#anc-textures-packing

    ORM: Occulsion Roughness Metallic
    ORMS: Occulsion Roughness Metallic Specular

    Texture Naming Style:

    Albedo/Diffuse: {Name}_D.{imageExtension} or
                    {Name}_D.<UDIM>.{imageExtension}

    Normal: {Name}_N.{imageExtension} or
            {Name}_N.<UDIM>.{imageExtension}
    ORM: {Name}_ORM.{imageExtension} or
         {Name}_ORM.<UDIM>.{imageExtension}

    """

    order = ValidateContentsOrder
    families = ['gltf']
    hosts = ['maya']
    label = 'GLTF Textures Name'
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]

    def process(self, instance):
        """Process all the nodes in the instance"""
        invalid = self.get_texture_shader_invalid(instance)
        if invalid:
            raise RuntimeError("Non PBS material found in "
                               "{0}".format(invalid))
        invalid = self.get_texture_node_invalid(instance)
        if invalid:
            raise RuntimeError("Related texture file "
                               "nodes not connected")
        invalid = self.get_texture_name_invalid(instance)
        if invalid:
            raise RuntimeError("Invalid texture name(s) found: "
                               "{0}".format(invalid))

    def get_texture_name_invalid(self, instance):

        invalid = set()
        shading_grp = self.shader_selection(instance)

        # get the materials related to the selected assets
        # get the file textures related to the PBS Shader
        # validate the names of the textures
        for material in shading_grp:
            main_shader = cmds.listConnections(material,
                                               destination=True,
                                               type="StingrayPBS")
            for shader in main_shader:
                albedo = cmds.listConnections(shader + ".TEX_color_map")[0]
                dif_path = cmds.getAttr(albedo + ".fileTextureName")
                dif = dif_path.split(".")[0]
                # "_D"
                if not dif.endswith("_D"):
                    invalid.add(dif_path)
                orm_packed = cmds.listConnections(shader + ".TEX_ao_mapX")[0]
                # "_ORM"
                orm_path = cmds.getAttr(orm_packed + ".fileTextureName")
                orm = orm_path.split(".")[0]
                if not orm.endswith("_ORM"):
                    invalid.add(orm_path)
                nrm = cmds.listConnections(shader + ".TEX_normal_map")[0]
                nrm_path = cmds.getAttr(nrm + ".fileTextureName")
                nrm_map = nrm_path.split(".")[0]
                # "_N"
                if not nrm_map.endswith("_N"):
                    invalid.add(nrm_path)

        return list(invalid)

    def get_texture_node_invalid(self, instance):
        invalid = set()
        shading_grp = self.shader_selection(instance)
        for material in shading_grp:
            main_shader = cmds.listConnections(material,
                                               destination=True,
                                               type="StingrayPBS")
            for shader in main_shader:
                # diffuse texture file node
                albedo = cmds.listConnections(shader + ".TEX_color_map")
                if not albedo:
                    invalid.add(albedo)
                orm_packed = cmds.listConnections(shader + ".TEX_ao_mapX")
                if not orm_packed:
                    invalid.add(orm_packed)
                nrm = cmds.listConnections(shader + ".TEX_normal_map")
                if not nrm:
                    invalid.add(nrm)
        return list(invalid)

    def get_texture_shader_invalid(self, instance):

        invalid = set()
        shading_grp = self.shader_selection(instance)
        for shader in shading_grp:
            if "StingrayPBS" not in shader:
                invalid.add(shader)
        return list(invalid)

    def shader_selection(self, instance):
        shapes = cmds.ls(instance, type="mesh", long=True)
        for shape in shapes:
            shading_grp = cmds.listConnections(shape,
                                               destination=True,
                                               type="shadingEngine")

            return shading_grp
