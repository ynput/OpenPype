import os
import shutil

import pype.api
from avalon import harmony


class ExtractTemplate(pype.api.Extractor):
    """Extract the connected nodes to the composite instance."""
    label = "Extract Template"
    hosts = ["harmony"]
    families = ["harmony.template"]

    def process(self, instance):
        staging_dir = self.staging_dir(instance)

        self.log.info("Outputting template to %s" % staging_dir)

        self.dependencies = []
        self.get_dependencies(instance[0])

        func = """function func(args)
        {
            var nodes = args[0];
            selection.clearSelection();
            for (var i = 0 ; i < nodes.length; i++)
            {
                selection.addNodeToSelection(nodes[i]);
            }
        }
        func
        """
        harmony.send({"function": func, "args": [self.dependencies]})
        func = """function func(args)
        {
            copyPaste.createTemplateFromSelection(args[0], args[1]);
        }
        func
        """
        harmony.send(
            {
                "function": func,
                "args": ["{}.tpl".format(instance.name), staging_dir]
            }
        )

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
            "stagingDir": staging_dir,
        }
        instance.data["representations"] = [representation]

    def get_dependencies(self, node):
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

        current_dependencies = harmony.send(
            {"function": func, "args": [node]}
        )["result"]

        for dependency in current_dependencies:
            if not dependency:
                continue

            if dependency in self.dependencies:
                continue

            self.dependencies.append(dependency)

            self.get_dependencies(dependency)
