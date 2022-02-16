import pyblish.api
import avalon.api


class SaveCurrentScene(pyblish.api.InstancePlugin):
    """Save current scene"""

    label = "Save current file"
    order = pyblish.api.ExtractorOrder - 0.49
    hosts = ["houdini"]
    families = ["usdrender",
                "redshift_rop"]
    targets = ["local"]

    def process(self, instance):

        # This should be a ContextPlugin, but this is a workaround
        # for a bug in pyblish to run once for a family: issue #250
        context = instance.context
        key = "__hasRun{}".format(self.__class__.__name__)
        if context.data.get(key, False):
            return
        else:
            context.data[key] = True

        # Filename must not have changed since collecting
        host = avalon.api.registered_host()
        current_file = host.current_file()
        assert context.data['currentFile'] == current_file, (
            "Collected filename from current scene name."
        )

        if host.has_unsaved_changes():
            self.log.info("Saving current file..")
            host.save_file(current_file)
        else:
            self.log.debug("No unsaved changes, skipping file save..")
