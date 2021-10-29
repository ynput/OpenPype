from maya import cmds

import pyblish.api
import openpype.api
import openpype.hosts.maya.api.action


class ValidateNodeNoGhosting(pyblish.api.InstancePlugin):
    """Ensure nodes do not have ghosting enabled.

    If one would publish towards a non-Maya format it's likely that stats
    like ghosting won't be exported, eg. exporting to Alembic.

    Instead of creating many micro-managing checks (like this one) to ensure
    attributes have not been changed from their default it could be more
    efficient to export to a format that will never hold such data anyway.

    """

    order = openpype.api.ValidateContentsOrder
    hosts = ['maya']
    families = ['model', 'rig']
    label = "No Ghosting"
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]

    _attributes = {'ghosting': 0}

    @classmethod
    def get_invalid(cls, instance):

        # Transforms and shapes seem to have ghosting
        nodes = cmds.ls(instance, long=True, type=['transform', 'shape'])
        invalid = []
        for node in nodes:
            _iteritems = getattr(
                cls._attributes, "iteritems", cls._attributes.items
            )
            for attr, required_value in _iteritems():
                if cmds.attributeQuery(attr, node=node, exists=True):

                    value = cmds.getAttr('{0}.{1}'.format(node, attr))
                    if value != required_value:
                        invalid.append(node)

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)

        if invalid:
            raise ValueError("Nodes with ghosting enabled found: "
                             "{0}".format(invalid))
