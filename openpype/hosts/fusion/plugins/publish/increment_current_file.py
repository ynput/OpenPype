import pyblish.api

from openpype.pipeline import OptionalPyblishPluginMixin
from openpype.pipeline import KnownPublishError


class FusionIncrementCurrentFile(
    pyblish.api.ContextPlugin, OptionalPyblishPluginMixin
):
    """Increment the current file.

    Saves the current file with an increased version number.

    """

    label = "Increment workfile version"
    order = pyblish.api.IntegratorOrder + 9.0
    hosts = ["fusion"]
    optional = True

    def process(self, context):
        if not self.is_active(context.data):
            return

        from openpype.lib import version_up
        from openpype.pipeline.publish import get_errored_plugins_from_context

        errored_plugins = get_errored_plugins_from_context(context)
        if any(
            plugin.__name__ == "FusionSubmitDeadline"
            for plugin in errored_plugins
        ):
            raise KnownPublishError(
                "Skipping incrementing current file because "
                "submission to render farm failed."
            )

        comp = context.data.get("currentComp")
        assert comp, "Must have comp"

        current_filepath = context.data["currentFile"]
        new_filepath = version_up(current_filepath)

        comp.Save(new_filepath)
