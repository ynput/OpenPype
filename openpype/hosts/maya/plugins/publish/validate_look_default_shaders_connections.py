import pyblish.api
from maya import cmds

from openpype.pipeline.publish import (
    OptionalPyblishPluginMixin,
    PublishValidationError,
    ValidateContentsOrder,
)


class ValidateLookDefaultShadersConnections(pyblish.api.InstancePlugin,
                                            OptionalPyblishPluginMixin):
    """Validate default shaders in the scene have their default connections.

    For example the lambert1 could potentially be disconnected from the
    initialShadingGroup. As such it's not lambert1 that will be identified
    as the default shader which can have unpredictable results.

    To fix the default connections need to be made again. See the logs for
    more details on which connections are missing.

    """

    order = ValidateContentsOrder
    families = ['look']
    hosts = ['maya']
    label = 'Look Default Shader Connections'

    # The default connections to check
    DEFAULTS = [("initialShadingGroup.surfaceShader", "lambert1"),
                ("initialParticleSE.surfaceShader", "lambert1"),
                ("initialParticleSE.volumeShader", "particleCloud1")
                ]

    def process(self, instance):

        # Ensure check is run only once. We don't use ContextPlugin because
        # of a bug where the ContextPlugin will always be visible. Even when
        # the family is not present in an instance.
        key = "__validate_look_default_shaders_connections_checked"
        context = instance.context
        is_run = context.data.get(key, False)
        if is_run:
            return
        else:
            context.data[key] = True

        # Process as usual
        invalid = list()
        for plug, input_node in self.DEFAULTS:
            inputs = cmds.listConnections(plug,
                                          source=True,
                                          destination=False) or None

            if not inputs or inputs[0] != input_node:
                self.log.error("{0} is not connected to {1}. "
                               "This can result in unexpected behavior. "
                               "Please reconnect to continue.".format(
                                plug,
                                input_node))
                invalid.append(plug)

        if invalid:
            raise PublishValidationError("Invalid connections.")
