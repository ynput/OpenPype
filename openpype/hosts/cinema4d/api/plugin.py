import c4d
from openpype.pipeline import (
    LegacyCreator
    )

from . import lib

class Creator(LegacyCreator):
    defaults = ['Main']

    def process(self):
        nodes = list()
        doc = c4d.documents.GetActiveDocument()
        #with lib.undo_chunk():
        if (self.options or {}).get("useSelection"):
            nodes = doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_CHILDREN)

        instance = lib.create_selection(nodes, name=self.name)
        lib.imprint(instance, self.data)

        return instance