import tempfile
import zipfile
import os
import shutil

from avalon import api
import openpype.hosts.harmony.api as harmony


class ImportTemplateLoader(api.Loader):
    """Import templates."""

    families = ["harmony.template", "workfile"]
    representations = ["*"]
    label = "Import Template"

    def load(self, context, name=None, namespace=None, data=None):
        # Import template.
        temp_dir = tempfile.mkdtemp()
        zip_file = api.get_representation_path(context["representation"])
        template_path = os.path.join(temp_dir, "temp.tpl")
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(template_path)

        sig = harmony.signature("paste")
        func = """function %s(args)
        {
            var template_path = args[0];
            var drag_object = copyPaste.pasteTemplateIntoGroup(
                template_path, "Top", 1
            );
        }
        %s
        """ % (sig, sig)

        harmony.send({"function": func, "args": [template_path]})

        shutil.rmtree(temp_dir)

        subset_name = context["subset"]["name"]

        return harmony.containerise(
            subset_name,
            namespace,
            subset_name,
            context,
            self.__class__.__name__
        )

        def update(self, container, representation):
            pass

        def remove(self, container):
            pass


class ImportWorkfileLoader(ImportTemplateLoader):
    """Import workfiles."""

    families = ["workfile"]
    representations = ["zip"]
    label = "Import Workfile"
