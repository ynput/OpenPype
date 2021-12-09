from openpype.lib.openpype_version import (
    get_remote_versions,
    get_OpenPypeVersion,
    get_build_version
)
from .input_entities import TextEntity
from .lib import (
    OverrideState,
    NOT_SET
)
from .exceptions import BaseInvalidValue


class OpenPypeVersionInput(TextEntity):
    def _item_initialization(self):
        super(OpenPypeVersionInput, self)._item_initialization()
        self.multiline = False
        self.placeholder_text = "Latest"
        self.value_hints = []

    def _get_openpype_versions(self):
        return []

    def set_override_state(self, state, *args, **kwargs):
        value_hints = []
        if state is OverrideState.STUDIO:
            versions = self._get_openpype_versions()
            if versions is not None:
                for version in versions:
                    value_hints.append(str(version))

        self.value_hints = value_hints

        super(OpenPypeVersionInput, self).set_override_state(
            state, *args, **kwargs
        )

    def convert_to_valid_type(self, value):
        if value and value is not NOT_SET:
            OpenPypeVersion = get_OpenPypeVersion()
            if OpenPypeVersion is not None:
                try:
                    OpenPypeVersion(version=value)
                except Exception:
                    raise BaseInvalidValue(
                        "Value \"{}\"is not valid version format.".format(
                            value
                        ),
                        self.path
                    )
        return super(OpenPypeVersionInput, self).convert_to_valid_type(value)


class ProductionVersionsInputEntity(OpenPypeVersionInput):
    schema_types = ["production-versions-text"]

    def _get_openpype_versions(self):
        versions = get_remote_versions(staging=False, production=True)
        versions.append(get_build_version())
        return sorted(versions)


class StagingVersionsInputEntity(OpenPypeVersionInput):
    schema_types = ["staging-versions-text"]

    def _get_openpype_versions(self):
        versions = get_remote_versions(staging=True, production=False)
        versions.append(get_build_version())
        return sorted(versions)
