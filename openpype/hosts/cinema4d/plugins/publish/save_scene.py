import pyblish.api
import os

class SaveCurrentScene(pyblish.api.ContextPlugin):
    """Save current scene

    """

    label = "Save current file"
    order = pyblish.api.ExtractorOrder - 0.49
    hosts = ["cinema4d"]
    #families = []

    def process(self, context):
        import c4d
        from openpype.hosts.cinema4d import api
        doc = c4d.documents.GetActiveDocument()

        
        assert context.data['currentFile'] == api.current_file()

        # If file has no modifications, skip forcing a file save
        if not api.has_unsaved_changes():
            self.log.debug("Skipping file save as there "
                           "are no modifications..")
            return

        self.log.info("Saving current file..")
        api.save_file(doc=doc)
