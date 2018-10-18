from maya import cmds

import pyblish.api
import colorbleed.api


class ValidateYetiRenderScriptCallbacks(pyblish.api.InstancePlugin):
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

    order = colorbleed.api.ValidateContentsOrder
    label = "Yeti Render Script Callbacks"
    hosts = ["maya"]
    families = ["colorbleed.renderlayer"]

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise ValueError("Invalid render callbacks found for '%s'!"
                             % instance.name)

    @classmethod
    def get_invalid(cls, instance):

        # lookup per render
        render_scripts = {"vray":
                              {"pre":  "catch(`pgYetiVRayPreRender`)",
                               "post": "catch(`pgYetiVRayPostRender`)"},
                          "arnold":
                              {"pre": "pgYetiPreRender"}
                          }

        yeti_loaded = cmds.pluginInfo("pgYetiMaya", query=True, loaded=True)

        renderer = instance.data["renderer"]
        if renderer == "redshift":
            cls.log.info("Redshift ignores any pre and post render callbacks")
            return False

        callback_lookup = render_scripts.get(renderer, {})
        if not callback_lookup:
            cls.log.warning("Renderer '%s' is not supported in this plugin"
                            % renderer)
            return False

        pre_mel_attr = "defaultRenderGlobals.preMel"
        post_mel_attr = "defaultRenderGlobals.postMel"

        pre_render_callback = cmds.getAttr(pre_mel_attr) or ""
        post_render_callback = cmds.getAttr(post_mel_attr) or ""

        pre_callbacks = pre_render_callback.split(";")
        post_callbacks = post_render_callback.split(";")

        pre_script = callback_lookup.get("pre", "")
        post_script = callback_lookup.get("post", "")

        # If not loaded
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
        else:
            if pre_script:
                if pre_script not in pre_callbacks:
                    cls.log.error(
                        "Could not find required pre render callback "
                        "`%s`" % pre_script)
                    invalid = True

            if post_script:
                if post_script not in post_callbacks:
                    cls.log.error("Could not find required post render callback"
                                  " `%s`" % post_script)
                    invalid = True

        return invalid
