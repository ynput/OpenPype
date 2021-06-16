import tempfile
import os
import pyblish.api
import avalon.api

from openpype.lib import get_subset_name

ValidatePipelineOrder = pyblish.api.ValidatorOrder + 0.05
ValidateContentsOrder = pyblish.api.ValidatorOrder + 0.1
ValidateSceneOrder = pyblish.api.ValidatorOrder + 0.2
ValidateMeshOrder = pyblish.api.ValidatorOrder + 0.3


class PypeCreatorMixin:
    """Helper to override avalon's default class methods.

    Mixin class must be used as first in inheritance order to override methods.
    """
    dynamic_subset_keys = []

    @classmethod
    def get_dynamic_data(
        cls, variant, task_name, asset_id, project_name, host_name
    ):
        """Return dynamic data for current Creator plugin.

        By default return keys from `dynamic_subset_keys` attribute as mapping
        to keep formatted template unchanged.

        ```
        dynamic_subset_keys = ["my_key"]
        ---
        output = {
            "my_key": "{my_key}"
        }
        ```

        Dynamic keys may override default Creator keys (family, task, asset,
        ...) but do it wisely if you need.

        All of keys will be converted into 3 variants unchanged, capitalized
        and all upper letters. Because of that are all keys lowered.

        This method can be modified to prefill some values just keep in mind it
        is class method.

        Returns:
            dict: Fill data for subset name template.
        """
        dynamic_data = {}
        for key in cls.dynamic_subset_keys:
            key = key.lower()
            dynamic_data[key] = "{" + key + "}"
        return dynamic_data

    @classmethod
    def get_subset_name(
        cls, variant, task_name, asset_id, project_name, host_name=None
    ):
        dynamic_data = cls.get_dynamic_data(
            variant, task_name, asset_id, project_name, host_name
        )

        return get_subset_name(
            cls.family,
            variant,
            task_name,
            asset_id,
            project_name,
            host_name,
            dynamic_data=dynamic_data
        )


class Creator(PypeCreatorMixin, avalon.api.Creator):
    pass


class ContextPlugin(pyblish.api.ContextPlugin):
    def process(cls, *args, **kwargs):
        super(ContextPlugin, cls).process(cls, *args, **kwargs)


class InstancePlugin(pyblish.api.InstancePlugin):
    def process(cls, *args, **kwargs):
        super(InstancePlugin, cls).process(cls, *args, **kwargs)


class Extractor(InstancePlugin):
    """Extractor base class.

    The extractor base class implements a "staging_dir" function used to
    generate a temporary directory for an instance to extract to.

    This temporary directory is generated through `tempfile.mkdtemp()`

    """

    order = 2.0

    def staging_dir(self, instance):
        """Provide a temporary directory in which to store extracted files

        Upon calling this method the staging directory is stored inside
        the instance.data['stagingDir']
        """
        staging_dir = instance.data.get('stagingDir', None)

        if not staging_dir:
            staging_dir = os.path.normpath(
                tempfile.mkdtemp(prefix="pyblish_tmp_")
            )
            instance.data['stagingDir'] = staging_dir

        return staging_dir


def contextplugin_should_run(plugin, context):
    """Return whether the ContextPlugin should run on the given context.

    This is a helper function to work around a bug pyblish-base#250
    Whenever a ContextPlugin sets specific families it will still trigger even
    when no instances are present that have those families.

    This actually checks it correctly and returns whether it should run.

    """
    required = set(plugin.families)

    # When no filter always run
    if "*" in required:
        return True

    for instance in context:

        # Ignore inactive instances
        if (not instance.data.get("publish", True) or
                not instance.data.get("active", True)):
            continue

        families = instance.data.get("families", [])
        if any(f in required for f in families):
            return True

        family = instance.data.get("family")
        if family and family in required:
            return True

    return False


class ValidationException(Exception):
    pass
