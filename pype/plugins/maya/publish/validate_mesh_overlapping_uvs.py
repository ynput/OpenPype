from maya import cmds

import pyblish.api
import pype.api
import pype.maya.action


class ValidateMeshHasOverlappingUVs(pyblish.api.InstancePlugin):
    """Validate the current mesh overlapping UVs.

    It validates whether the current UVs are overlapping or not.
    It is optional to warn publisher about it.
    """

    order = pype.api.ValidateMeshOrder
    hosts = ['maya']
    families = ['model']
    category = 'geometry'
    label = 'Mesh Has Overlapping UVs'
    actions = [pype.maya.action.SelectInvalidAction]
    optional = True

    @classmethod
    def _has_overlapping_uvs(cls, node):

        allUvSets = cmds.polyUVSet(q=1, auv=1)
        # print allUvSets
        currentTool = cmds.currentCtx()
        cmds.setToolTo('selectSuperContext')
        biglist = cmds.ls(
            cmds.polyListComponentConversion(node, tf=True), fl=True)
        shells = []
        overlappers = []
        bounds = []
        for uvset in allUvSets:
            # print uvset
            while len(biglist) > 0:
                cmds.select(biglist[0], r=True)
                # cmds.polySelectConstraint(t=0)
                # cmds.polySelectConstraint(sh=1,m=2)
                # cmds.polySelectConstraint(sh=0,m=0)
                aShell = cmds.ls(sl=True, fl=True)
                shells.append(aShell)
                biglist = list(set(biglist) - set(aShell))
                cmds.setToolTo(currentTool)
                cmds.select(clear=True)
                # shells = [ [faces in uv shell 1], [faces in shell 2], [etc] ]

            for faces in shells:
                shellSets = cmds.polyListComponentConversion(
                    faces, ff=True, tuv=True)
                if shellSets != []:
                    uv = cmds.polyEditUV(shellSets, q=True)

                    uMin = uv[0]
                    uMax = uv[0]
                    vMin = uv[1]
                    vMax = uv[1]
                    for i in range(len(uv)/2):
                        if uv[i*2] < uMin:
                            uMin = uv[i*2]
                        if uv[i*2] > uMax:
                            uMax = uv[i*2]
                        if uv[i*2+1] < vMin:
                            vMin = uv[i*2+1]
                        if uv[i*2+1] > vMax:
                            vMax = uv[i*2+1]
                        bounds.append([[uMin, uMax], [vMin, vMax]])
                else:
                    return False

        for a in range(len(shells)):
            for b in range(a):
                # print "b",b
                if bounds != []:
                    # print bounds
                    aL = bounds[a][0][0]
                    aR = bounds[a][0][1]
                    aT = bounds[a][1][1]
                    aB = bounds[a][1][0]

                    bL = bounds[b][0][0]
                    bR = bounds[b][0][1]
                    bT = bounds[b][1][1]
                    bB = bounds[b][1][0]

                    overlaps = True
                    if aT < bB:  # A entirely below B
                        overlaps = False

                    if aB > bT:  # A entirely above B
                        overlaps = False

                    if aR < bL:  # A entirely right of B
                        overlaps = False

                    if aL > bR:  # A entirely left of B
                        overlaps = False

                    if overlaps:
                        overlappers.extend(shells[a])
                        overlappers.extend(shells[b])
                else:
                    return False
                    pass

        if overlappers:
            return True
        else:
            return False

    @classmethod
    def get_invalid(cls, instance):
        invalid = []

        for node in cmds.ls(instance, type='mesh'):
            if cls._has_overlapping_uvs(node):
                invalid.append(node)

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Meshes found with overlapping "
                               "UVs: {0}".format(invalid))
        pass
