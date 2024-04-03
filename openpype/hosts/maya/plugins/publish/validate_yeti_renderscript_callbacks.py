from maya import cmds

import pyblish.api
from openpype.pipeline.publish import (
    ValidateContentsOrder,
    OptionalPyblishPluginMixin
)


class ValidateYetiRenderScriptCallbacks(pyblish.api.InstancePlugin,
                                        OptionalPyblishPluginMixin):
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
    optional = False

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

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        invalid = self.get_invalid(instance)
        if invalid:
            raise ValueError("Invalid render callbacks found for '%s'!"
                             % instance.name)

    @classmethod
    def get_invalid(cls, instance):

        yeti_loaded = cmds.pluginInfo("pgYetiMaya", query=True, loaded=True)

        if not yeti_loaded and not cmds.ls(type="pgYetiMaya"):
            # The yeti plug-in is available and loaded so at
            # this point we don't really care whether the scene
            # has any yeti callback set or not since if the callback
            # is there it wouldn't error and if it weren't then
            # nothing happens because there are no yeti nodes.
            cls.log.debug(
                "Yeti is loaded but no yeti nodes were found. "
                "Callback validation skipped.."
            )
            return False

        renderer = instance.data["renderer"]
        if renderer == "redshift":
            cls.log.debug("Redshift ignores any pre and post render callbacks")
            return False

        callback_lookup = cls.callbacks.get(renderer, {})
        if not callback_lookup:
            cls.log.warning("Renderer '%s' is not supported in this plugin"
                            % renderer)
            return False

        pre_mel = cmds.getAttr("defaultRenderGlobals.preMel") or ""
        post_mel = cmds.getAttr("defaultRenderGlobals.postMel") or ""

        if pre_mel.strip():
            cls.log.debug("Found pre mel: `%s`" % pre_mel)

        if post_mel.strip():
            cls.log.debug("Found post mel: `%s`" % post_mel)

        # Strip callbacks and turn into a set for quick lookup
        pre_callbacks = {cmd.strip() for cmd in pre_mel.split(";")}
        post_callbacks = {cmd.strip() for cmd in post_mel.split(";")}

        pre_script = callback_lookup.get("pre", "")
        post_script = callback_lookup.get("post", "")

        # If Yeti is not loaded
        invalid = False
        if not yeti_loaded:
            if pre_script and pre_script in pre_callbacks:
                cls.log.error("Found pre render callback '%s' which is not "
                              "uses!" % pre_script)
                invalid = True

            if post_script and post_script in post_callbacks:
                cls.log.error("Found post render callback '%s which is "
                              "not used!" % post_script)
                invalid = True

        # If Yeti is loaded
        else:
            if pre_script and pre_script not in pre_callbacks:
                cls.log.error(
                    "Could not find required pre render callback "
                    "`%s`" % pre_script)
                invalid = True

            if post_script and post_script not in post_callbacks:
                cls.log.error(
                    "Could not find required post render callback"
                    " `%s`" % post_script)
                invalid = True

        return invalid
