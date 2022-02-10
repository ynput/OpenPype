import pyblish.api
import openpype.api
import string

import six

# Allow only characters, numbers and underscore
allowed = set(string.ascii_lowercase +
              string.ascii_uppercase +
              string.digits +
              '_')


def validate_name(subset):
    return all(x in allowed for x in subset)


class ValidateSubsetName(pyblish.api.InstancePlugin):
    """Validates subset name has only valid characters"""

    order = openpype.api.ValidateContentsOrder
    families = ["*"]
    label = "Subset Name"

    def process(self, instance):

        subset = instance.data.get("subset", None)

        # Ensure subset data
        if subset is None:
            raise RuntimeError("Instance is missing subset "
                               "name: {0}".format(subset))

        if not isinstance(subset, six.string_types):
            raise TypeError("Instance subset name must be string, "
                            "got: {0} ({1})".format(subset, type(subset)))

        # Ensure is not empty subset
        if not subset:
            raise ValueError("Instance subset name is "
                             "empty: {0}".format(subset))

        # Validate subset characters
        if not validate_name(subset):
            raise ValueError("Instance subset name contains invalid "
                             "characters: {0}".format(subset))
