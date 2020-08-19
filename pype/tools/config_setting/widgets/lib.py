from .config import OVERRIDEN_KEY


class CustomNone:
    """Created object can be used as custom None (not equal to None)."""
    def __bool__(self):
        """Return False (like default None)."""
        return False


NOT_SET = CustomNone()
AS_WIDGET = type("AS_WIDGET", (), {})

METADATA_KEY = type("METADATA_KEY", (), {})

OVERRIDE_VERSION = 1


def convert_gui_data_to_overrides(data, first=True):
    if not data or not isinstance(data, dict):
        return data

    output = {}
    if first:
        output["__override_version__"] = OVERRIDE_VERSION

    if METADATA_KEY in data:
        metadata = data.pop(METADATA_KEY)
        for key, value in metadata.items():
            if key == "groups":
                print("**", value)
                output[OVERRIDEN_KEY] = value
            else:
                KeyError("Unknown metadata key \"{}\"".format(key))

    for key, value in data.items():
        output[key] = convert_gui_data_to_overrides(value, False)
    return output


def convert_overrides_to_gui_data(data, first=True):
    if not data or not isinstance(data, dict):
        return data

    output = {}
    if OVERRIDEN_KEY in data:
        groups = data.pop(OVERRIDEN_KEY)
        if METADATA_KEY not in output:
            output[METADATA_KEY] = {}
        output[METADATA_KEY]["groups"] = groups

    for key, value in data.items():
        output[key] = convert_overrides_to_gui_data(value, False)

    return output
