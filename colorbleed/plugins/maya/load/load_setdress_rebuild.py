from avalon import api


class SetDressRebuild(api.Loader):

    families = ["colorbleed.setdress"]
    representations = ["json"]

    label = "Rebuild Set Dress"
    order = -9
    icon = "code-fork"
    color = "orange"

    def process(self, name, namespace, context, data):

        import json
        from maya import cmds
        from avalon.tools.cbloader import lib
        from colorbleed.maya import lib as clib
        from cb.utils.maya import core

        with open(self.fname, "r") as fp:
            build_data = json.load(fp)

        cmds.namespace(add=namespace)

        new_transforms = []
        for representation_id, instances in build_data.items():

            # Find the corresponding loader
            loaders = list(lib.iter_loaders(representation_id))

            # Ensure context can be passed on
            for inst in instances:
                # Get the used loader
                Loader = next((x for x in loaders if
                               x.__name__ == inst['loader']),
                              None)

                if Loader is None:
                    self.log.warning("Loader is missing: %s. Skipping %s",
                                     inst['loader'], inst)
                    continue

                # Run the loader
                instance_ns = ":".join([namespace,
                                        inst['namespace'].strip(":")])
                container = lib.run_loader(Loader,
                                           representation_id,
                                           namespace=instance_ns)

                container_data = {"objectName": container}
                transforms = clib.get_container_transforms(container_data)
                # Force sort order, similar to collector
                transforms = sorted(transforms)

                for idx, matrix in inst["matrix"].items():
                    cmds.xform(transforms[int(idx)], matrix=matrix)

                # Store the created container
                self.append(container)
                new_transforms.extend(transforms)

        roots = core.getHighestInHierarchy(new_transforms)
        cmds.group(roots, name="{}:{}".format(namespace,
                                              context['subset']['name']))
