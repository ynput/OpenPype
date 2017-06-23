import pprint
from avalon import api


class AbcLoader(api.Loader):
    """Specific loader of Alembic for the avalon.animation family"""

    families = ["colorbleed.animation", "colorbleed.camera"]
    representations = ["abc"]

    def process(self, name, namespace, context):
        from maya import cmds

        cmds.loadPlugin("AbcImport.mll", quiet=True)
        # Prevent identical alembic nodes from being shared
        # Create unique namespace for the cameras

        nodes = cmds.file(self.fname,
                          namespace=namespace,
                          sharedReferenceFile=False,
                          groupReference=True,
                          groupName="{}:{}".format(namespace, name),
                          reference=True,
                          returnNewNodes=True)

        self[:] = nodes


class CurvesLoader(api.Loader):
    """Specific loader of Curves for the avalon.animation family"""

    families = ["colorbleed.animation"]
    representations = ["curves"]

    def process(self, name, namespace, context):
        from maya import cmds
        from avalon import maya

        cmds.loadPlugin("atomImportExport.mll", quiet=True)

        rig = context["representation"]["dependencies"][0]
        container = maya.load(rig,
                              name=name,
                              namespace=namespace,
                              # Skip creation of Animation instance
                              post_process=False)

        try:
            control_set = next(
                node for node in cmds.sets(container, query=True)
                if node.endswith("controls_SET")
            )
        except StopIteration:
            raise TypeError("%s is missing controls_SET")

        cmds.select(control_set)
        options = ";".join([
            "",
            "",
            "targetTime=3",
            "option=insert",
            "match=hierarchy",
            "selected=selectedOnly",
            "search=",
            "replace=",
            "prefix=",
            "suffix=",
            "mapFile=",
        ])

        with maya.maintained_selection():
            cmds.select(
                control_set,
                replace=True,

                # Support controllers being embedded in
                # additional selection sets.
                noExpand=False
            )

            nodes = cmds.file(
                self.fname,
                i=True,
                type="atomImport",
                renameAll=True,
                namespace=namespace,
                options=options,
                returnNewNodes=True,
            )

        self[:] = nodes + cmds.sets(container, query=True) + [container]

    def post_process(self, name, namespace, context):
        import os
        from maya import cmds
        from avalon import maya, io

        # Task-dependent post-process
        if os.getenv("AVALON_TASK") != "animate":
            return self.log.info(
                "No animation instance created due to task != animate"
            )

        # Find associated rig to these curves
        try:
            dependency = context["representation"]["dependencies"][0]
        except (KeyError, IndexError):
            return self.log.warning("No dependencies found for %s" % name)

        dependency = io.find_one({"_id": io.ObjectId(dependency)})
        _, _, dependency, _ = io.parenthood(dependency)

        # TODO(marcus): We are hardcoding the name "out_SET" here.
        #   Better register this keyword, so that it can be used
        #   elsewhere, such as in the Integrator plug-in,
        #   without duplication.
        output = next((node for node in self
                       if node.endswith("out_SET")), None)
        controls = next((node for node in self
                         if node.endswith("controls_SET")), None)

        assert output, "No out_SET in rig, this is a bug."
        assert controls, "No controls_SET in rig, this is a bug."

        with maya.maintained_selection():
            cmds.select([output, controls], noExpand=True)

            dependencies = [context["representation"]["_id"]]
            name = "anim{}_".format(dependency["name"].title())

            # TODO(marcus): Hardcoding the family here, better separate this.
            family = [f for f in self.families if f.endswith("animation")]
            assert len(family) == 1, ("None or multiple animation "
                                      "families found")
            family = family[0]
            maya.create(
                name=maya.unique_name(name, suffix="_SET"),
                family=family,
                options={"useSelection": True},
                data={"dependencies": " ".join(str(d) for d in dependencies)})


class HistoryLoader(api.Loader):
    """Specific loader of Curves for the avalon.animation family"""

    families = ["colorbleed.animation"]
    representations = ["history"]

    def process(self, name, namespace, context):
        raise NotImplementedError("Can't load history yet.")
