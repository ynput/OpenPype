import pyblish.api
import pype.api
import pype.hosts.maya.action
import math
import maya.api.OpenMaya as om
import pymel.core as pm


class GetOverlappingUVs(object):

    def _createBoundingCircle(self, meshfn):
        """ Represent a face by center and radius

            :param meshfn: MFnMesh class
            :type meshfn: :class:`maya.api.OpenMaya.MFnMesh`
            :returns: (center, radius)
            :rtype: tuple
        """
        center = []
        radius = []
        for i in xrange(meshfn.numPolygons):  # noqa: F821
            # get uvs from face
            uarray = []
            varray = []
            for j in range(len(meshfn.getPolygonVertices(i))):
                uv = meshfn.getPolygonUV(i, j)
                uarray.append(uv[0])
                varray.append(uv[1])

            # loop through all vertices to construct edges/rays
            cu = 0.0
            cv = 0.0
            for j in range(len(uarray)):
                cu += uarray[j]
                cv += varray[j]

            cu /= len(uarray)
            cv /= len(varray)
            rsqr = 0.0
            for j in range(len(varray)):
                du = uarray[j] - cu
                dv = varray[j] - cv
                dsqr = du * du + dv * dv
                rsqr = dsqr if dsqr > rsqr else rsqr

            center.append(cu)
            center.append(cv)
            radius.append(math.sqrt(rsqr))

        return center, radius

    def _createRayGivenFace(self, meshfn, faceId):
        """ Represent a face by a series of edges(rays), i.e.

            :param meshfn: MFnMesh class
            :type meshfn: :class:`maya.api.OpenMaya.MFnMesh`
            :param faceId: face id
            :type faceId: int
            :returns: False if no valid uv's.
                      ""(True, orig, vec)"" or ""(False, None, None)""
            :rtype: tuple

            .. code-block:: python

            orig = [orig1u, orig1v, orig2u, orig2v, ... ]
            vec  = [vec1u,  vec1v,  vec2u,  vec2v,  ... ]
        """
        orig = []
        vec = []
        # get uvs
        uarray = []
        varray = []
        for i in range(len(meshfn.getPolygonVertices(faceId))):
            uv = meshfn.getPolygonUV(faceId, i)
            uarray.append(uv[0])
            varray.append(uv[1])

        if len(uarray) == 0 or len(varray) == 0:
            return (False, None, None)

        # loop throught all vertices to construct edges/rays
        u = uarray[-1]
        v = varray[-1]
        for i in xrange(len(uarray)):  # noqa: F821
            orig.append(uarray[i])
            orig.append(varray[i])
            vec.append(u - uarray[i])
            vec.append(v - varray[i])
            u = uarray[i]
            v = varray[i]

        return (True, orig, vec)

    def _checkCrossingEdges(self,
                            face1Orig,
                            face1Vec,
                            face2Orig,
                            face2Vec):
        """ Check if there are crossing edges between two faces.
            Return True if there are crossing edges and False otherwise.

            :param face1Orig: origin of face 1
            :type face1Orig: tuple
            :param face1Vec: face 1 edges
            :type face1Vec: list
            :param face2Orig: origin of face 2
            :type face2Orig: tuple
            :param face2Vec: face 2 edges
            :type face2Vec: list

            A face is represented by a series of edges(rays), i.e.
            .. code-block:: python

               faceOrig[] = [orig1u, orig1v, orig2u, orig2v, ... ]
               faceVec[]  = [vec1u,  vec1v,  vec2u,  vec2v,  ... ]
        """
        face1Size = len(face1Orig)
        face2Size = len(face2Orig)
        for i in xrange(0, face1Size, 2):  # noqa: F821
            o1x = face1Orig[i]
            o1y = face1Orig[i+1]
            v1x = face1Vec[i]
            v1y = face1Vec[i+1]
            n1x = v1y
            n1y = -v1x
            for j in xrange(0, face2Size, 2):  # noqa: F821
                # Given ray1(O1, V1) and ray2(O2, V2)
                # Normal of ray1 is (V1.y, V1.x)
                o2x = face2Orig[j]
                o2y = face2Orig[j+1]
                v2x = face2Vec[j]
                v2y = face2Vec[j+1]
                n2x = v2y
                n2y = -v2x

                # Find t for ray2
                # t = [(o1x-o2x)n1x + (o1y-o2y)n1y] /
                # (v2x * n1x + v2y * n1y)
                denum = v2x * n1x + v2y * n1y
                # Edges are parallel if denum is close to 0.
                if math.fabs(denum) < 0.000001:
                    continue
                t2 = ((o1x-o2x) * n1x + (o1y-o2y) * n1y) / denum
                if (t2 < 0.00001 or t2 > 0.99999):
                    continue

                # Find t for ray1
                # t = [(o2x-o1x)n2x
                # + (o2y-o1y)n2y] / (v1x * n2x + v1y * n2y)
                denum = v1x * n2x + v1y * n2y
                # Edges are parallel if denum is close to 0.
                if math.fabs(denum) < 0.000001:
                    continue
                t1 = ((o2x-o1x) * n2x + (o2y-o1y) * n2y) / denum

                # Edges intersect
                if (t1 > 0.00001 and t1 < 0.99999):
                    return 1

        return 0

    def _getOverlapUVFaces(self, meshName):
        """ Return overlapping faces

            :param meshName: name of mesh
            :type meshName: str
            :returns: list of overlapping faces
            :rtype: list
        """
        faces = []
        # find polygon mesh node
        selList = om.MSelectionList()
        selList.add(meshName)
        mesh = selList.getDependNode(0)
        if mesh.apiType() == om.MFn.kTransform:
            dagPath = selList.getDagPath(0)
            dagFn = om.MFnDagNode(dagPath)
            child = dagFn.child(0)
            if child.apiType() != om.MFn.kMesh:
                raise Exception("Can't find polygon mesh")
            mesh = child
        meshfn = om.MFnMesh(mesh)

        center, radius = self._createBoundingCircle(meshfn)
        for i in xrange(meshfn.numPolygons):  # noqa: F821
            rayb1, face1Orig, face1Vec = self._createRayGivenFace(
                                                    meshfn, i)
            if not rayb1:
                continue
            cui = center[2*i]
            cvi = center[2*i+1]
            ri = radius[i]
            # Exclude the degenerate face
            # if(area(face1Orig) < 0.000001) continue;
            # Loop through face j where j != i
            for j in range(i+1, meshfn.numPolygons):
                cuj = center[2*j]
                cvj = center[2*j+1]
                rj = radius[j]
                du = cuj - cui
                dv = cvj - cvi
                dsqr = du * du + dv * dv
                # Quick rejection if bounding circles don't overlap
                if (dsqr >= (ri + rj) * (ri + rj)):
                    continue

                rayb2, face2Orig, face2Vec = self._createRayGivenFace(
                                                    meshfn, j)
                if not rayb2:
                    continue
                # Exclude the degenerate face
                # if(area(face2Orig) < 0.000001): continue;
                if self._checkCrossingEdges(face1Orig,
                                            face1Vec,
                                            face2Orig,
                                            face2Vec):
                    face1 = '%s.f[%d]' % (meshfn.name(), i)
                    face2 = '%s.f[%d]' % (meshfn.name(), j)
                    if face1 not in faces:
                        faces.append(face1)
                    if face2 not in faces:
                        faces.append(face2)
        return faces


class ValidateMeshHasOverlappingUVs(pyblish.api.InstancePlugin):
    """ Validate the current mesh overlapping UVs.

    It validates whether the current UVs are overlapping or not.
    It is optional to warn publisher about it.
    """

    order = pype.api.ValidateMeshOrder
    hosts = ['maya']
    families = ['model']
    category = 'geometry'
    label = 'Mesh Has Overlapping UVs'
    actions = [pype.hosts.maya.action.SelectInvalidAction]
    optional = True

    @classmethod
    def _get_overlapping_uvs(cls, node):
        """ Check if mesh has overlapping UVs.

            :param node: node to check
            :type node: str
            :returns: True is has overlapping UVs, False otherwise
            :rtype: bool
        """
        ovl = GetOverlappingUVs()

        overlapping_faces = []
        for i, uv in enumerate(pm.polyUVSet(node, q=1, auv=1)):
            pm.polyUVSet(node, cuv=1, uvSet=uv)
            overlapping_faces.extend(ovl._getOverlapUVFaces(str(node)))

        return overlapping_faces

    @classmethod
    def get_invalid(cls, instance, compute=False):
        invalid = []
        if compute:
            instance.data["overlapping_faces"] = []
            for node in pm.ls(instance, type="mesh"):
                faces = cls._get_overlapping_uvs(node)
                invalid.extend(faces)
                # Store values for later.
                instance.data["overlapping_faces"].extend(faces)
        else:
            invalid.extend(instance.data["overlapping_faces"])

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance, compute=True)
        if invalid:
            raise RuntimeError(
                "Meshes found with overlapping UVs: {0}".format(invalid)
            )
