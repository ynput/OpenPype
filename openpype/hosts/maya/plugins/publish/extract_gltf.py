import os

from maya import cmds, mel
import pyblish.api

from openpype.pipeline import publish
from openpype.hosts.maya.api import lib
from openpype.hosts.maya.api.gltf import extract_gltf


class ExtractGLB(publish.Extractor):

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract GLB"
    families = ["gltf"]

    def process(self, instance):
        staging_dir = self.staging_dir(instance)
        filename = "{0}.glb".format(instance.name)
        path = os.path.join(staging_dir, filename)

        self.log.info("Extracting GLB to: {}".format(path))

        nodes = instance[:]

        self.log.info("Instance: {0}".format(nodes))

        start_frame = instance.data('frameStart') or \
                      int(cmds.playbackOptions(query=True,
                                               animationStartTime=True))# noqa
        end_frame = instance.data('frameEnd') or \
                    int(cmds.playbackOptions(query=True,
                                             animationEndTime=True)) # noqa
        fps = mel.eval('currentTimeUnitToFPS()')

        options = {
            "sno": True,    # selectedNodeOnly
            "nbu": True,    # .bin instead of .bin0
            "ast": start_frame,
            "aet": end_frame,
            "afr": fps,
            "dsa": 1,
            "acn": instance.name,
            "glb": True,
            "vno": True    # visibleNodeOnly
        }

        # convert to gltf shader
        self.convert_gltf_shader(instance)

        with lib.maintained_selection():
            cmds.select(nodes, hi=True, noExpand=True)
            extract_gltf(staging_dir,
                         instance.name,
                         **options)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'glb',
            'ext': 'glb',
            'files': filename,
            "stagingDir": staging_dir,
        }
        instance.data["representations"].append(representation)

        self.log.info("Extract GLB successful to: {0}".format(path))

    def convert_gltf_shader(self, instance):
        """
        Converting StingrayPBS material to GLSL Shaders
        specially for the glb export through Maya2GLTF plugin
        """

        meshes = cmds.ls(instance, type="mesh", long=True)
        self.log.info("meshes: {}".format(meshes))
        # load the glsl shader plugin
        cmds.loadPlugin("glslShader", quiet=True)

        for mesh in meshes:

            # create glsl shader
            glsl = cmds.createNode('GLSLShader')
            glsl_shadingGrp = cmds.sets(name=glsl + "SG", empty=True,
                                        renderable=True, noSurfaceShader=True)
            cmds.connectAttr(glsl + ".outColor",
                             glsl_shadingGrp + ".surfaceShader")

            # load the maya2gltf shader
            ogsfx_path = instance.context.data["project_settings"]["maya"]["publish"]["ExtractGLB"]["ogsfx_path"]  # noqa
            if not os.path.exists(ogsfx_path):
                if ogsfx_path:
                # studio settings have a custom ogsfx_
                # path set. If the path is not specified,
                # this log will warn the user.
                    self.log.warning("ogsfx shader file not found in {}".format(ogsfx_path))

                self.log.info("Find the ogsfx shader file in "
                              "default maya directory...")
                # re-direct to search the ogsfx path in maya_dir
                ogsfx_path = os.getenv("MAYA_APP_DIR") + ogsfx_path
                if not os.path.exists(ogsfx_path):
                    raise RuntimeError("The ogsfx shader file does not "
                                       "exist: {}".format(ogsfx_path))

            cmds.setAttr(glsl + ".shader", ogsfx_path, typ="string")

            # list the materials used for the assets
            shading_grp = cmds.listConnections(mesh,
                                               destination=True,
                                               type="shadingEngine")

            # get the materials related to the selected assets
            for material in shading_grp:
                main_shader = cmds.listConnections(material,
                                                   destination=True,
                                                   type="StingrayPBS")
                for shader in main_shader:
                    # get the file textures related to the PBS Shader
                    albedo = cmds.listConnections(shader + ".TEX_color_map")
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
                    nrm = cmds.listConnections(shader + ".TEX_normal_map")
                    if nrm:
                        nrm_output = nrm[0] + ".outColor"
                        glsl_nrm = glsl + ".u_NormalTexture"
                        cmds.connectAttr(nrm_output, glsl_nrm)

            # assign the shader to the asset
            cmds.sets(mesh, forceElement=str(glsl_shadingGrp))
