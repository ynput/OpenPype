import os

from maya import cmds

from avalon import api, maya


class AbcLoader(api.Loader):
    """Specific loader of Alembic for the avalon.animation family"""

    families = ["colorbleed.animation", "colorbleed.camera"]
    representations = ["abc"]

    label = "Reference animation"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process(self, name, namespace, context, data):

        cmds.loadPlugin("AbcImport.mll", quiet=True)
        # Prevent identical alembic nodes from being shared
        # Create unique namespace for the cameras

        # Get name from asset being loaded
        # Assuming name is subset name from the animation, we split the number
        # suffix from the name to ensure the namespace is unique
        name = name.split("_")[0]
        namespace = maya.unique_namespace("{}_".format(name),
                                          format="%03d",
                                          suffix="_abc")

        # hero_001 (abc)
        # asset_counter{optional}

        nodes = cmds.file(self.fname,
                          namespace=namespace,
                          sharedReferenceFile=False,
                          groupReference=True,
                          groupName="{}:{}".format(namespace, name),
                          reference=True,
                          returnNewNodes=True)

        # load colorbleed ID attribute
        self[:] = nodes


class CurvesLoader(api.Loader):
    """Specific loader of Curves for the avalon.animation family"""

    families = ["colorbleed.animation"]
    representations = ["curves"]

    label = "Import curves"
    order = -1
    icon = "question"

    def process(self, name, namespace, context, data):

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
            cmds.select(control_set,
                        replace=True,
                        # Support controllers being embedded in
                        # additional selection sets.
                        noExpand=False)

            nodes = cmds.file(self.fname,
                              i=True,
                              type="atomImport",
                              renameAll=True,
                              namespace=namespace,
                              options=options,
                              returnNewNodes=True)

        self[:] = nodes + cmds.sets(container, query=True) + [container]

        if data.get("post_process", True):
            self._post_process(name, namespace, context, data)

    def _post_process(self, name, namespace, context, data):

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
            dependencies = " ".join(str(d) for d in dependencies)
            name = "anim{}_".format(dependency["name"].title())

            # TODO(marcus): Hardcoding the family here, better separate this.
            family = [f for f in self.families if f.endswith("animation")]
            assert len(family) == 1, ("None or multiple animation "
                                      "families found")
            family = family[0]
            maya.create(name=maya.unique_name(name, suffix="_SET"),
                        family=family,
                        options={"useSelection": True},
                        data={"dependencies": dependencies})
