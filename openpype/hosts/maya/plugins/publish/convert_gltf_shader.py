import os
from maya import cmds
import pyblish.api

from openpype.pipeline import publish


class ConvertGLSLShader(publish.Extractor):
    """
    Converting StingrayPBS material to GLSL Shaders
    specially for the glb export through Maya2GLTF plugin

    """
    order = pyblish.api.ExtractorOrder - 0.1
    hosts = ["maya"]
    label = "Convert StingrayPBS to GLTF"
    families = ["gltf"]
    optional = True

    def process(self, instance):
        meshes = cmds.ls(instance, type="mesh", long=True)
        self.log.info("meshes: {}".format(meshes))
        # load the glsl shader plugin
        cmds.loadPlugin("glslShader.mll", quiet=True)

        for mesh in meshes:

            # create glsl shader
            glsl_shader = cmds.createNode('GLSLShader')
            glsl_shadingGrp = cmds.sets(name=glsl_shader + "SG", empty=True,
                                        renderable=True, noSurfaceShader=True)
            cmds.connectAttr(glsl_shader + ".outColor", glsl_shadingGrp + ".surfaceShader")

            # load the maya2gltf shader
            maya_dir = os.getenv("MAYA_APP_DIR")
            ogsfx = maya_dir + "/maya2glTF/PBR/shaders/glTF_PBR.ogsfx"
            cmds.setAttr(glsl_shader + ".shader", ogsfx, typ="string")

            # list the materials used for the assets
            shading_grp = cmds.listConnections(
                mesh, destination=True, type="shadingEngine"
            )

            # get the materials related to the selected assets
            for material in shading_grp:
                main_shader = cmds.listConnections(
                material, destination=True, type="StingrayPBS"
            )
                for shader in main_shader:
                    # get the file textures related to the PBS Shader
                    albedo = cmds.listConnections(shader + ".TEX_color_map")[0]
                    dif_output = albedo + ".outColor"

                    orm_packed = cmds.listConnections(shader + ".TEX_ao_mapX")[0]
                    ao_output = orm_packed + ".outColorR"
                    rough_output = orm_packed + ".outColorG"
                    metallic_output = orm_packed + ".outColorB"

                    nrm = cmds.listConnections(shader + ".TEX_normal_map")[0]
                    nrm_output = nrm + ".outColor"

                    # get the glsl_shader input
                    # reconnect the file nodes to maya2gltf shader
                    glsl_dif = glsl_shader + ".u_BaseColorTexture"
                    glsl_nrm = glsl_shader + ".u_NormalTexture"
                    cmds.connectAttr(dif_output, glsl_dif)
                    cmds.connectAttr(nrm_output, glsl_nrm)

                    rgb_list = ["R", "G", "B"]
                    for ch in rgb_list:
                        mtl = ".u_MetallicTexture.u_MetallicTexture{}".format(ch)
                        mtl = glsl_shader + mtl
                        ao = ".u_OcclusionTexture.u_OcclusionTexture{}".format(ch)
                        ao= glsl_shader + ao
                        rough = ".u_RoughnessTexture.u_RoughnessTexture{}".format(ch)
                        rough= glsl_shader + rough

                        cmds.connectAttr(metallic_output, mtl)
                        cmds.connectAttr(ao_output, ao)
                        cmds.connectAttr(rough_output, rough)

            # assign the shader to the asset
            cmds.sets(mesh, forceElement = str(glsl_shadingGrp))
