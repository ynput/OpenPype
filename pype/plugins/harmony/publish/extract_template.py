import os
import shutil

import pype.api
import avalon.harmony
import pype.hosts.harmony


class ExtractTemplate(pype.api.Extractor):
    """Extract the connected nodes to the composite instance."""

    label = "Extract Template"
    hosts = ["harmony"]
    families = ["harmony.template"]

    def process(self, instance):
        staging_dir = self.staging_dir(instance)
        filepath = os.path.join(staging_dir, "{}.tpl".format(instance.name))

        self.log.info("Outputting template to {}".format(staging_dir))

        dependencies = []
        self.get_dependencies(instance[0], dependencies)

        # Get backdrops.
        backdrops = {}
        for dependency in dependencies:
            for backdrop in self.get_backdrops(dependency):
                backdrops[backdrop["title"]["text"]] = backdrop
        unique_backdrops = [backdrops[x] for x in set(backdrops.keys())]

        # Get non-connected nodes within backdrops.
        all_nodes = avalon.harmony.send(
            {"function": "node.subNodes", "args": ["Top"]}
        )["result"]
        for node in [x for x in all_nodes if x not in dependencies]:
            within_unique_backdrops = bool(
                [x for x in self.get_backdrops(node) if x in unique_backdrops]
            )
            if within_unique_backdrops:
                dependencies.append(node)

        # Make sure we dont export the instance node.
        if instance[0] in dependencies:
            dependencies.remove(instance[0])

        # Export template.
        pype.hosts.harmony.export_template(
            unique_backdrops, dependencies, filepath
        )

        # Prep representation.
        os.chdir(staging_dir)
        shutil.make_archive(
            "{}".format(instance.name),
            "zip",
            os.path.join(staging_dir, "{}.tpl".format(instance.name))
        )

        representation = {
            "name": "tpl",
            "ext": "zip",
            "files": "{}.zip".format(instance.name),
            "stagingDir": staging_dir
        }
        instance.data["representations"] = [representation]

    def get_backdrops(self, node):
        func = """function func(probe_node)
        {
            var backdrops = Backdrop.backdrops("Top");
            var valid_backdrops = [];
            for(var i=0; i<backdrops.length; i++)
            {
                var position = backdrops[i].position;

                var x_valid = false;
                var node_x = node.coordX(probe_node);
                if (position.x < node_x && node_x < (position.x + position.w)){
                    x_valid = true
                };

                var y_valid = false;
                var node_y = node.coordY(probe_node);
                if (position.y < node_y && node_y < (position.y + position.h)){
                    y_valid = true
                };

                if (x_valid && y_valid){
                    valid_backdrops.push(backdrops[i])
                };
            }
            return valid_backdrops;
        }
        func
        """
        return avalon.harmony.send(
            {"function": func, "args": [node]}
        )["result"]

    def get_dependencies(self, node, dependencies):
        func = """function func(args)
        {
            var target_node = args[0];
            var numInput = node.numberOfInputPorts(target_node);
            var dependencies = [];
            for (var i = 0 ; i < numInput; i++)
            {
                dependencies.push(node.srcNode(target_node, i));
            }
            return dependencies;
        }
        func
        """

        current_dependencies = avalon.harmony.send(
            {"function": func, "args": [node]}
        )["result"]

        for dependency in current_dependencies:
            if not dependency:
                continue

            if dependency in dependencies:
                continue

            dependencies.append(dependency)

            self.get_dependencies(dependency, dependencies)
