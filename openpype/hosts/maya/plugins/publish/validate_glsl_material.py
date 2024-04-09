import os
from maya import cmds

import pyblish.api
from openpype.pipeline.publish import (
    RepairAction,
    ValidateContentsOrder
)
from openpype.pipeline import (
    PublishValidationError,
    OptionalPyblishPluginMixin
)


class ValidateGLSLMaterial(pyblish.api.InstancePlugin,
                           OptionalPyblishPluginMixin):
    """
    Validate if the asset uses GLSL Shader
    """

    order = ValidateContentsOrder + 0.1
    families = ['gltf']
    hosts = ['maya']
    label = 'GLSL Shader for GLTF'
    actions = [RepairAction]
    optional = True
    active = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        shading_grp = self.get_material_from_shapes(instance)
        if not shading_grp:
            raise PublishValidationError("No shading group found")
        invalid = self.get_texture_shader_invalid(instance)
        if invalid:
            raise PublishValidationError("Non GLSL Shader found: "
                                         "{0}".format(invalid))

    def get_material_from_shapes(self, instance):
        shapes = cmds.ls(instance, type="mesh", long=True)
        for shape in shapes:
            shading_grp = cmds.listConnections(shape,
                                               destination=True,
                                               type="shadingEngine")

            return shading_grp or []

    def get_texture_shader_invalid(self, instance):

        invalid = set()
        shading_grp = self.get_material_from_shapes(instance)
        for shading_group in shading_grp:
            material_name = "{}.surfaceShader".format(shading_group)
            material = cmds.listConnections(material_name,
                                            source=True,
                                            destination=False,
                                            type="GLSLShader")

            if not material:
                # add material name
                material = cmds.listConnections(material_name)[0]
                invalid.add(material)

        return list(invalid)

    @classmethod
    def repair(cls, instance):
        """
        Repair instance by assigning GLSL Shader
        to the material
        """
        cls.assign_glsl_shader(instance)
        return

    @classmethod
    def assign_glsl_shader(cls, instance):
        """
        Converting StingrayPBS material to GLSL Shaders
        for the glb export through Maya2GLTF plugin
        """

        meshes = cmds.ls(instance, type="mesh", long=True)
        cls.log.debug("meshes: {}".format(meshes))
        # load the glsl shader plugin
        cmds.loadPlugin("glslShader", quiet=True)

        for mesh in meshes:
            # create glsl shader
            glsl = cmds.createNode('GLSLShader')
            glsl_shading_grp = cmds.sets(name=glsl + "SG", empty=True,
                                         renderable=True, noSurfaceShader=True)
            cmds.connectAttr(glsl + ".outColor",
                             glsl_shading_grp + ".surfaceShader")

            # load the maya2gltf shader
            ogsfx_path = instance.context.data["project_settings"]["maya"]["publish"]["ExtractGLB"]["ogsfx_path"]  # noqa
            if not os.path.exists(ogsfx_path):
                if ogsfx_path:
                    # if custom ogsfx path is not specified
                    # the log below is the warning for the user
                    cls.log.warning("ogsfx shader file "
                                    "not found in {}".format(ogsfx_path))

                cls.log.debug("Searching the ogsfx shader file in "
                              "default maya directory...")
                # re-direct to search the ogsfx path in maya_dir
                ogsfx_path = os.getenv("MAYA_APP_DIR") + ogsfx_path
                if not os.path.exists(ogsfx_path):
                    raise PublishValidationError("The ogsfx shader file does not "      # noqa
                                                 "exist: {}".format(ogsfx_path))        # noqa

            cmds.setAttr(glsl + ".shader", ogsfx_path, typ="string")
            # list the materials used for the assets
            shading_grp = cmds.listConnections(mesh,
                                               destination=True,
                                               type="shadingEngine")

            # get the materials related to the selected assets
            for material in shading_grp:
                pbs_shader = cmds.listConnections(material,
                                                  destination=True,
                                                  type="StingrayPBS")
                if pbs_shader:
                    cls.pbs_shader_conversion(pbs_shader, glsl)
                # setting up to relink the texture if
                # the mesh is with aiStandardSurface
                arnold_shader = cmds.listConnections(material,
                                                     destination=True,
                                                     type="aiStandardSurface")
                if arnold_shader:
                    cls.arnold_shader_conversion(arnold_shader, glsl)

            cmds.sets(mesh, forceElement=str(glsl_shading_grp))

    @classmethod
    def pbs_shader_conversion(cls, main_shader, glsl):

        cls.log.debug("StringrayPBS detected "
                      "-> Can do texture conversion")

        for shader in main_shader:
            # get the file textures related to the PBS Shader
            albedo = cmds.listConnections(shader +
                                          ".TEX_color_map")
            if albedo:
                dif_output = albedo[0] + ".outColor"
                # get the glsl_shader input
                # reconnect the file nodes to maya2gltf shader
                glsl_dif = glsl + ".u_BaseColorTexture"
                cmds.connectAttr(dif_output, glsl_dif)

            # connect orm map if there is one
            orm_packed = cmds.listConnections(shader +
                                              ".TEX_ao_map")
            if orm_packed:
                orm_output = orm_packed[0] + ".outColor"

                mtl = glsl + ".u_MetallicTexture"
                ao = glsl + ".u_OcclusionTexture"
                rough = glsl + ".u_RoughnessTexture"

                cmds.connectAttr(orm_output, mtl)
                cmds.connectAttr(orm_output, ao)
                cmds.connectAttr(orm_output, rough)

            # connect nrm map if there is one
            nrm = cmds.listConnections(shader +
                                       ".TEX_normal_map")
            if nrm:
                nrm_output = nrm[0] + ".outColor"
                glsl_nrm = glsl + ".u_NormalTexture"
                cmds.connectAttr(nrm_output, glsl_nrm)

    @classmethod
    def arnold_shader_conversion(cls, main_shader, glsl):
        cls.log.debug("aiStandardSurface detected "
                      "-> Can do texture conversion")

        for shader in main_shader:
            # get the file textures related to the PBS Shader
            albedo = cmds.listConnections(shader + ".baseColor")
            if albedo:
                dif_output = albedo[0] + ".outColor"
                # get the glsl_shader input
                # reconnect the file nodes to maya2gltf shader
                glsl_dif = glsl + ".u_BaseColorTexture"
                cmds.connectAttr(dif_output, glsl_dif)

            orm_packed = cmds.listConnections(shader +
                                              ".specularRoughness")
            if orm_packed:
                orm_output = orm_packed[0] + ".outColor"

                mtl = glsl + ".u_MetallicTexture"
                ao = glsl + ".u_OcclusionTexture"
                rough = glsl + ".u_RoughnessTexture"

                cmds.connectAttr(orm_output, mtl)
                cmds.connectAttr(orm_output, ao)
                cmds.connectAttr(orm_output, rough)

            # connect nrm map if there is one
            bump_node = cmds.listConnections(shader +
                                             ".normalCamera")
            if bump_node:
                for bump in bump_node:
                    nrm = cmds.listConnections(bump +
                                               ".bumpValue")
                    if nrm:
                        nrm_output = nrm[0] + ".outColor"
                        glsl_nrm = glsl + ".u_NormalTexture"
                        cmds.connectAttr(nrm_output, glsl_nrm)
