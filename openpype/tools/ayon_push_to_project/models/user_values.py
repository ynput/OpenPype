import re

from openpype.pipeline.create import SUBSET_NAME_ALLOWED_SYMBOLS


class UserPublishValuesModel:
    """Helper object to validate values required for push to different project.

    Args:
        controller (PushToContextController): Event system to catch
            and emit events.
    """

    folder_name_regex = re.compile("^[a-zA-Z0-9_.]+$")
    variant_regex = re.compile("^[{}]+$".format(SUBSET_NAME_ALLOWED_SYMBOLS))

    def __init__(self, controller):
        self._controller = controller
        self._new_folder_name = None
        self._variant = None
        self._comment = None
        self._is_variant_valid = False
        self._is_new_folder_name_valid = False

        self.set_new_folder_name("")
        self.set_variant("")
        self.set_comment("")

    @property
    def new_folder_name(self):
        return self._new_folder_name

    @property
    def variant(self):
        return self._variant

    @property
    def comment(self):
        return self._comment

    @property
    def is_variant_valid(self):
        return self._is_variant_valid

    @property
    def is_new_folder_name_valid(self):
        return self._is_new_folder_name_valid

    @property
    def is_valid(self):
        return self.is_variant_valid and self.is_new_folder_name_valid

    def get_data(self):
        return {
            "new_folder_name": self._new_folder_name,
            "variant": self._variant,
            "comment": self._comment,
            "is_variant_valid": self._is_variant_valid,
            "is_new_folder_name_valid": self._is_new_folder_name_valid,
            "is_valid": self.is_valid
        }

    def set_variant(self, variant):
        if variant == self._variant:
            return

        self._variant = variant
        is_valid = False
        if variant:
            is_valid = self.variant_regex.match(variant) is not None
        self._is_variant_valid = is_valid

        self._controller.emit_event(
            "variant.changed",
            {
                "variant": variant,
                "is_valid": self._is_variant_valid,
            },
            "user_values"
        )

    def set_new_folder_name(self, folder_name):
        if self._new_folder_name == folder_name:
            return

        self._new_folder_name = folder_name
        is_valid = True
        if folder_name:
            is_valid = (
                self.folder_name_regex.match(folder_name) is not None
            )
        self._is_new_folder_name_valid = is_valid
        self._controller.emit_event(
            "new_folder_name.changed",
            {
                "new_folder_name": self._new_folder_name,
                "is_valid": self._is_new_folder_name_valid,
            },
            "user_values"
        )

    def set_comment(self, comment):
        if comment == self._comment:
            return
        self._comment = comment
        self._controller.emit_event(
            "comment.changed",
            {"comment": comment},
            "user_values"
        )
