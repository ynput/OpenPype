from maya import cmds

import pyblish.api
from openpype.pipeline.publish import (
    context_plugin_should_run,
    filter_instances_for_context_plugin,
    ValidateContentsOrder,
    RepairContextAction,
    PublishValidationError
)


class ValidateYetiRenderScriptCallbacks(pyblish.api.ContextPlugin):
    """Check if the render script callbacks will be used during the rendering

    In order to ensure the render tasks are executed properly we need to check
    if the pre and post render callbacks are actually used.

    For example:
        Yeti is not loaded but its callback scripts are still set in the
        render settings. This will cause an error because Maya tries to find
        and execute the callbacks.

    Developer note:
         The pre and post render callbacks cannot be overridden

    """

    order = ValidateContentsOrder
    label = "Yeti Render Script Callbacks"
    hosts = ["maya"]
    families = ["renderlayer"]
    actions = [RepairContextAction]

    # Settings per renderer
    callbacks = {
        "vray": {
            "pre": "catch(`pgYetiVRayPreRender`)",
            "post": "catch(`pgYetiVRayPostRender`)"
        },
        "arnold": {
            "pre": "pgYetiPreRender"
        }
    }

    def process(self, context):
        # Workaround bug pyblish-base#250
        if not context_plugin_should_run(self, context):
            return

        invalid = self.get_invalid(context)
        if invalid:
            raise PublishValidationError(
                "Invalid Yeti render callbacks found."
            )

    @classmethod
    def get_invalid(cls, context):

        yeti_loaded = cmds.pluginInfo("pgYetiMaya", query=True, loaded=True)
        if yeti_loaded and not cmds.ls(type="pgYetiMaya"):
            # The yeti plug-in is available and loaded so at
            # this point we don't really care whether the scene
            # has any yeti callback set or not since if the callback
            # is there it wouldn't error and if it weren't then
            # nothing happens because there are no yeti nodes.
            cls.log.debug(
                "Yeti is loaded but no yeti nodes were found. "
                "Callback validation skipped.."
            )
            return {}

        # For all renderlayer instances find the renderer used, so we ensure
        # to validate the callback for any unique supported renderer
        instances = filter_instances_for_context_plugin(plugin=cls,
                                                        context=context)
        renderers = set(instance.data["renderer"] for instance in instances)
        all_invalid = []
        for renderer in renderers:
            invalid = cls.validate_for_renderer(renderer, yeti_loaded)
            if invalid:
                all_invalid.extend(invalid)

        return invalid

    @classmethod
    def validate_for_renderer(cls, renderer, yeti_loaded):

        if renderer == "redshift":
            cls.log.debug("Redshift ignores any pre and post render callbacks")
            return False

        callback_lookup = cls.callbacks.get(renderer, {})
        if not callback_lookup:
            cls.log.warning("Renderer '%s' is not supported in this plugin"
                            % renderer)
            return []

        invalid = []
        for when, yeti_callback in callback_lookup.items():
            attr = "defaultRenderGlobals.{}Mel".format(when)  # pre or post
            current = (cmds.getAttr(attr) or "").strip()      # current value
            if current:
                cls.log.debug("Found {} mel: `{}`".format(when, current))

            # Strip callbacks and turn into a set for quick lookup
            current_callbacks = {cmd.strip() for cmd in current.split(";")}

            if yeti_loaded and yeti_callback not in current_callbacks:
                cls.log.error(
                    "Could not find required {} render callback '{}' for Yeti."
                    .format(when, yeti_callback)
                )
                invalid.append((attr, True, yeti_callback))
            elif not yeti_loaded and yeti_callback in current_callbacks:
                cls.log.error(
                    "Found {} render callback '{}' while Yeti is not used!"
                    .format(when, yeti_callback)
                )
                invalid.append((attr, False, yeti_callback))

        return invalid

    @classmethod
    def repair(cls, context):
        invalid = cls.get_invalid(context)
        if not invalid:
            cls.log.info("Nothing to repair.")

        for attr, add, callback in invalid:
            current = (cmds.getAttr(attr) or "").strip()
            if add:
                # Add callback
                if not current.endswith(";"):
                    current += ";"
                new = "{}{};".format(current, callback)
                cmds.setAttr(attr, new, type="string")
            else:
                # Remove callback
                new = ";".join(
                    cmd for cmd in current.split(";")
                    if cmd.strip() != callback
                )
                cmds.setAttr(attr, new, type="string")
