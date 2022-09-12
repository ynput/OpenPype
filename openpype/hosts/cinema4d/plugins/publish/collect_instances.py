import c4d
import pyblish.api
import json
from openpype.hosts.cinema4d.api import lib



class CollectInstances(pyblish.api.ContextPlugin):
    """Gather instances by objectSet and pre-defined attribute

    This collector takes into account assets that are associated with
    an objectSet and marked with a unique identifier;

    Identifier:
        id (str): "pyblish.avalon.instance"

    Limitations:
        - Does not take into account nodes connected to those
            within an objectSet. Extractors are assumed to export
            with history preserved, but this limits what they will
            be able to achieve and the amount of data available
            to validators. An additional collector could also
            append this input data into the instance, as we do
            for `pype.rig` with collect_history.

    """

    label = "Collect Instances"
    order = pyblish.api.CollectorOrder
    hosts = ["cinema4d"]

    def process(self, context, doc=None):
        if not doc:
            doc = c4d.documents.GetActiveDocument()

        objectset = set()
        for obj in lib.walk_hierarchy(doc.GetFirstObject()):
            if obj.attrs.get("id"):
                objectset.add(obj.attrs)


        ctx_frame_start = context.data['frameStart']
        ctx_frame_end = context.data['frameEnd']
        ctx_handle_start = context.data['handleStart']
        ctx_handle_end = context.data['handleEnd']
        ctx_frame_start_handle = context.data['frameStartHandle']
        ctx_frame_end_handle = context.data['frameEndHandle']

        context.data['objectsets'] = objectset
        for objset in objectset:

            if not objset.get("id"):
                continue

            if objset.get("id") != "pyblish.avalon.instance":
                continue

            # The developer is responsible for specifying
            # the family of each instance.
            has_family = objset.get("family")
            assert has_family, "\"%s\" was missing a family" % objset

            members = objset.get("SELECTIONOBJECT_LIST")
            if members is None:
                self.log.warning("Skipped empty instance: \"%s\" " % objset)
                continue

            self.log.info("Creating instance for {}".format(lib.serialize_c4d_data(objset.op)))

            data = dict()

            for key, value in objset:
                data[key] = lib.serialize_c4d_data(value)

            # temporarily translation of `active` to `publish` till issue has
            # been resolved, https://github.com/pyblish/pyblish-base/issues/307
            if "active" in data:
                data["publish"] = data["active"]

            # Collect members - c4d.BaseObject
            members = [lib.ObjectPath(obj=members.ObjectFromIndex(doc, idx)) for idx in range(members.GetObjectCount())]


            # Collect Children - c4d.BaseObject
            children = [lib.ObjectPath(obj=obj) for member in members for obj in lib.walk_hierarchy(member.obj.GetDown())]

            parents = []
            if data.get("includeParentHierarchy", True):
                # If `includeParentHierarchy` then include the parents
                # so they will also be picked up in the instance by validators
                parents = [lib.ObjectPath(obj=obj) for obj in self.get_all_parents(members)]
            members_hierarchy = list(
                    set(
                        [str(x) for x in members] + \
                        [str(x) for x in children] + \
                        [str(x) for x in parents]
                    )
                )

            if 'families' not in data:
                data['families'] = [data.get('family')]

            # Create the instance
            instance = context.create_instance(objset.op.GetName())
            instance[:] = members_hierarchy

            # Store the exact members of the object set
            instance.data["setMembers"] = [lib.serialize_c4d_data(x) for x in members]

            # Define nice label
            name = objset.op.GetName()  # use short name
            label = "{0} ({1})".format(name,
                                       data["asset"])

            # Append start frame and end frame to label if present
            if "frameStart" and "frameEnd" in data:

                # if frame range on maya set is the same as full shot range
                # adjust the values to match the asset data
                if (ctx_frame_start_handle == data["frameStart"]
                        and ctx_frame_end_handle == data["frameEnd"]):  # noqa: W503, E501
                    data["frameStartHandle"] = ctx_frame_start_handle
                    data["frameEndHandle"] = ctx_frame_end_handle
                    data["frameStart"] = ctx_frame_start
                    data["frameEnd"] = ctx_frame_end
                    data["handleStart"] = ctx_handle_start
                    data["handleEnd"] = ctx_handle_end

                # if there are user values on start and end frame not matching
                # the asset, use them

                else:
                    if "handles" in data:
                        data["handleStart"] = data["handles"]
                        data["handleEnd"] = data["handles"]
                    else:
                        data["handleStart"] = 0
                        data["handleEnd"] = 0

                    data["frameStartHandle"] = data["frameStart"] - data["handleStart"]  # noqa: E501
                    data["frameEndHandle"] = data["frameEnd"] + data["handleEnd"]  # noqa: E501

                if "handles" in data:
                    data.pop('handles')

                label += "  [{0}-{1}]".format(int(data["frameStartHandle"]),
                                              int(data["frameEndHandle"]))

            instance.data["label"] = label

            instance.data.update(data)

            # Produce diagnostic message for any graphical
            # user interface interested in visualising it.
            self.log.info("Found: \"%s\" " % instance.data["name"])
            self.log.debug(
                "DATA: {} ".format(json.dumps(instance.data, indent=4)))

        def sort_by_family(instance):
            """Sort by family"""
            return instance.data.get("families", instance.data.get("family"))

        # Sort/grouped by family (preserving local index)
        context[:] = sorted(context, key=sort_by_family)

        return context

    def get_all_parents(self, nodes):
        """Get all parents by using string operations (optimization)

        Args:
            nodes (list): the nodes which are found in the objectSet

        Returns:
            list
        """

        parents = []
        for node in nodes:
            parent = node.obj.GetUp()
            while parent:
                parents.append(parent)
                parent = parent.GetUp()

        return list(set(parents))
