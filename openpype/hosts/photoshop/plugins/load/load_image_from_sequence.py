import os

import qargparse
from avalon.pipeline import get_representation_path_from_context

from openpype.hosts.photoshop import api as photoshop
from openpype.hosts.photoshop.api import get_unique_layer_name


class ImageFromSequenceLoader(photoshop.PhotoshopLoader):
    """ Load specific image from sequence

        Used only as quick load of reference file from a sequence.

        Plain ImageLoader picks first frame from sequence.

        Loads only existing files - currently not possible to limit loaders
        to single select - multiselect. If user selects multiple repres, list
        for all of them is provided, but selection is only single file.
        This loader will be triggered multiple times, but selected name will
        match only to proper path.

        Loader doesnt do containerization as there is currently no data model
        of 'frame of rendered files' (only rendered sequence), update would be
        difficult.
    """

    families = ["render"]
    representations = ["*"]
    options = []

    def load(self, context, name=None, namespace=None, data=None):
        if data.get("frame"):
            self.fname = os.path.join(
                os.path.dirname(self.fname), data["frame"]
            )
            if not os.path.exists(self.fname):
                return

        stub = self.get_stub()
        layer_name = get_unique_layer_name(
            stub.get_layers(), context["asset"]["name"], name
        )

        with photoshop.maintained_selection():
            layer = stub.import_smart_object(self.fname, layer_name)

        self[:] = [layer]
        namespace = namespace or layer_name

        return namespace

    @classmethod
    def get_options(cls, repre_contexts):
        """
            Returns list of files for selected 'repre_contexts'.

            It returns only files with same extension as in context as it is
            expected that context points to sequence of frames.

            Returns:
                (list) of qargparse.Choice
        """
        files = []
        for context in repre_contexts:
            fname = get_representation_path_from_context(context)
            _, file_extension = os.path.splitext(fname)

            for file_name in os.listdir(os.path.dirname(fname)):
                if not file_name.endswith(file_extension):
                    continue
                files.append(file_name)

        # return selection only if there is something
        if not files or len(files) <= 1:
            return []

        return [
            qargparse.Choice(
                "frame",
                label="Select specific file",
                items=files,
                default=0,
                help="Which frame should be loaded?"
            )
        ]

    def update(self, container, representation):
        """No update possible, not containerized."""
        pass

    def remove(self, container):
        """No update possible, not containerized."""
        pass
