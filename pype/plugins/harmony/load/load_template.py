import tempfile
import zipfile
import os
import shutil

from avalon import api, harmony


class ImportTemplateLoader(api.Loader):
    """Import templates."""

    families = ["harmony.template"]
    representations = ["*"]
    label = "Import Template"

    def load(self, context, name=None, namespace=None, data=None):
        # Make backdrops from metadata.
        backdrops = context["representation"]["data"].get("backdrops", [])

        func = """function func(args)
        {
            Backdrop.addBackdrop("Top", args[0]);
        }
        func
        """
        for backdrop in backdrops:
            harmony.send({"function": func, "args": [backdrop]})

        # Import template.
        temp_dir = tempfile.mkdtemp()
        zip_file = api.get_representation_path(context["representation"])
        template_path = os.path.join(temp_dir, "temp.tpl")
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(template_path)

        func = """function func(args)
        {
            var template_path = args[0];
            var drag_object = copyPaste.copyFromTemplate(
                template_path, 0, 0, copyPaste.getCurrentCreateOptions()
            );
            copyPaste.pasteNewNodes(
                drag_object, "", copyPaste.getCurrentPasteOptions()
            );
        }
        func
        """

        func = """function func(args)
        {
            var template_path = args[0];
            var drag_object = copyPaste.pasteTemplateIntoGroup(
                template_path, "Top", 1
            );
        }
        func
        """

        harmony.send({"function": func, "args": [template_path]})

        shutil.rmtree(temp_dir)
