import os
import re
import copy
import numbers
import collections

import six

from .log import PypeLogger

log = PypeLogger.get_logger(__name__)


KEY_PATTERN = re.compile(r"(\{.*?[^{0]*\})")
KEY_PADDING_PATTERN = re.compile(r"([^:]+)\S+[><]\S+")
SUB_DICT_PATTERN = re.compile(r"([^\[\]]+)")
OPTIONAL_PATTERN = re.compile(r"(<.*?[^{0]*>)[^0-9]*?")


def merge_dict(main_dict, enhance_dict):
    """Merges dictionaries by keys.

    Function call itself if value on key is again dictionary.

    Args:
        main_dict (dict): First dict to merge second one into.
        enhance_dict (dict): Second dict to be merged.

    Returns:
        dict: Merged result.

    .. note:: does not overrides whole value on first found key
              but only values differences from enhance_dict

    """
    for key, value in enhance_dict.items():
        if key not in main_dict:
            main_dict[key] = value
        elif isinstance(value, dict) and isinstance(main_dict[key], dict):
            main_dict[key] = merge_dict(main_dict[key], value)
        else:
            main_dict[key] = value
    return main_dict


class TemplateMissingKey(Exception):
    """Exception for cases when key does not exist in template."""

    msg = "Template key does not exist: `{}`."

    def __init__(self, parents):
        parent_join = "".join(["[\"{0}\"]".format(key) for key in parents])
        super(TemplateMissingKey, self).__init__(
            self.msg.format(parent_join)
        )


class TemplateUnsolved(Exception):
    """Exception for unsolved template when strict is set to True."""

    msg = "Template \"{0}\" is unsolved.{1}{2}"
    invalid_types_msg = " Keys with invalid DataType: `{0}`."
    missing_keys_msg = " Missing keys: \"{0}\"."

    def __init__(self, template, missing_keys, invalid_types):
        invalid_type_items = []
        for _key, _type in invalid_types.items():
            invalid_type_items.append(
                "\"{0}\" {1}".format(_key, str(_type))
            )

        invalid_types_msg = ""
        if invalid_type_items:
            invalid_types_msg = self.invalid_types_msg.format(
                ", ".join(invalid_type_items)
            )

        missing_keys_msg = ""
        if missing_keys:
            missing_keys_msg = self.missing_keys_msg.format(
                ", ".join(missing_keys)
            )
        super(TemplateUnsolved, self).__init__(
            self.msg.format(template, missing_keys_msg, invalid_types_msg)
        )


class StringTemplate(object):
    """String that can be formatted."""
    def __init__(self, template):
        if not isinstance(template, six.string_types):
            raise TypeError("<{}> argument must be a string, not {}.".format(
                self.__class__.__name__, str(type(template))
            ))

        self._template = template
        parts = []
        last_end_idx = 0
        for item in KEY_PATTERN.finditer(template):
            start, end = item.span()
            if start > last_end_idx:
                parts.append(template[last_end_idx:start])
            parts.append(FormattingPart(template[start:end]))
            last_end_idx = end

        if last_end_idx < len(template):
            parts.append(template[last_end_idx:len(template)])

        new_parts = []
        for part in parts:
            if not isinstance(part, six.string_types):
                new_parts.append(part)
                continue

            substr = ""
            for char in part:
                if char not in ("<", ">"):
                    substr += char
                else:
                    if substr:
                        new_parts.append(substr)
                    new_parts.append(char)
                    substr = ""
            if substr:
                new_parts.append(substr)

        self._parts = self.find_optional_parts(new_parts)

    def __str__(self):
        return self.template

    def __repr__(self):
        return "<{}> {}".format(self.__class__.__name__, self.template)

    def __contains__(self, other):
        return other in self.template

    def replace(self, *args, **kwargs):
        self._template = self.template.replace(*args, **kwargs)
        return self

    @property
    def template(self):
        return self._template

    def format(self, data):
        """ Figure out with whole formatting.

        Separate advanced keys (*Like '{project[name]}') from string which must
        be formatted separatelly in case of missing or incomplete keys in data.

        Args:
            data (dict): Containing keys to be filled into template.

        Returns:
            TemplateResult: Filled or partially filled template containing all
                data needed or missing for filling template.
        """
        result = TemplatePartResult()
        for part in self._parts:
            if isinstance(part, six.string_types):
                result.add_output(part)
            else:
                part.format(data, result)

        invalid_types = result.invalid_types
        invalid_types.update(result.invalid_optional_types)
        invalid_types = result.split_keys_to_subdicts(invalid_types)

        missing_keys = result.missing_keys
        missing_keys |= result.missing_optional_keys

        solved = result.solved
        used_values = result.get_clean_used_values()

        return TemplateResult(
            result.output,
            self.template,
            solved,
            used_values,
            missing_keys,
            invalid_types
        )

    def format_strict(self, *args, **kwargs):
        result = self.format(*args, **kwargs)
        result.validate()
        return result

    @classmethod
    def format_template(cls, template, data):
        objected_template = cls(template)
        return objected_template.format(data)

    @classmethod
    def format_strict_template(cls, template, data):
        objected_template = cls(template)
        return objected_template.format_strict(data)

    @staticmethod
    def find_optional_parts(parts):
        new_parts = []
        tmp_parts = {}
        counted_symb = -1
        for part in parts:
            if part == "<":
                counted_symb += 1
                tmp_parts[counted_symb] = []

            elif part == ">":
                if counted_symb > -1:
                    parts = tmp_parts.pop(counted_symb)
                    counted_symb -= 1
                    if parts:
                        # Remove optional start char
                        parts.pop(0)
                        if counted_symb < 0:
                            out_parts = new_parts
                        else:
                            out_parts = tmp_parts[counted_symb]
                        # Store temp parts
                        out_parts.append(OptionalPart(parts))
                    continue

            if counted_symb < 0:
                new_parts.append(part)
            else:
                tmp_parts[counted_symb].append(part)

        if tmp_parts:
            for idx in sorted(tmp_parts.keys()):
                new_parts.extend(tmp_parts[idx])
        return new_parts


class TemplatesDict(object):
    def __init__(self, templates=None):
        self._raw_templates = None
        self._templates = None
        self._objected_templates = None
        self.set_templates(templates)

    def set_templates(self, templates):
        if templates is None:
            self._raw_templates = None
            self._templates = None
            self._objected_templates = None
        elif isinstance(templates, dict):
            self._raw_templates = copy.deepcopy(templates)
            self._templates = templates
            self._objected_templates = self.create_ojected_templates(templates)
        else:
            raise TypeError("<{}> argument must be a dict, not {}.".format(
                self.__class__.__name__, str(type(templates))
            ))

    def __getitem__(self, key):
        return self.templates[key]

    def get(self, key, *args, **kwargs):
        return self.templates.get(key, *args, **kwargs)

    @property
    def raw_templates(self):
        return self._raw_templates

    @property
    def templates(self):
        return self._templates

    @property
    def objected_templates(self):
        return self._objected_templates

    @classmethod
    def create_ojected_templates(cls, templates):
        if not isinstance(templates, dict):
            raise TypeError("Expected dict object, got {}".format(
                str(type(templates))
            ))

        objected_templates = copy.deepcopy(templates)
        inner_queue = collections.deque()
        inner_queue.append(objected_templates)
        while inner_queue:
            item = inner_queue.popleft()
            if not isinstance(item, dict):
                continue
            for key in tuple(item.keys()):
                value = item[key]
                if isinstance(value, six.string_types):
                    item[key] = StringTemplate(value)
                elif isinstance(value, dict):
                    inner_queue.append(value)
        return objected_templates

    def _format_value(self, value, data):
        if isinstance(value, StringTemplate):
            return value.format(data)

        if isinstance(value, dict):
            return self._solve_dict(value, data)
        return value

    def _solve_dict(self, templates, data):
        """ Solves templates with entered data.

        Args:
            templates (dict): All templates which will be formatted.
            data (dict): Containing keys to be filled into template.

        Returns:
            dict: With `TemplateResult` in values containing filled or
                partially filled templates.
        """
        output = collections.defaultdict(dict)
        for key, value in templates.items():
            output[key] = self._format_value(value, data)

        return output

    def format(self, in_data, only_keys=True, strict=True):
        """ Solves templates based on entered data.

        Args:
            data (dict): Containing keys to be filled into template.
            only_keys (bool, optional): Decides if environ will be used to
                fill templates or only keys in data.

        Returns:
            TemplatesResultDict: Output `TemplateResult` have `strict`
                attribute set to True so accessing unfilled keys in templates
                will raise exceptions with explaned error.
        """
        # Create a copy of inserted data
        data = copy.deepcopy(in_data)

        # Add environment variable to data
        if only_keys is False:
            for key, val in os.environ.items():
                env_key = "$" + key
                if env_key not in data:
                    data[env_key] = val

        solved = self._solve_dict(self.objected_templates, data)

        output = TemplatesResultDict(solved)
        output.strict = strict
        return output


class TemplateResult(str):
    """Result of template format with most of information in.

    Args:
        used_values (dict): Dictionary of template filling data with
            only used keys.
        solved (bool): For check if all required keys were filled.
        template (str): Original template.
        missing_keys (list): Missing keys that were not in the data. Include
            missing optional keys.
        invalid_types (dict): When key was found in data, but value had not
            allowed DataType. Allowed data types are `numbers`,
            `str`(`basestring`) and `dict`. Dictionary may cause invalid type
            when value of key in data is dictionary but template expect string
            of number.
    """
    used_values = None
    solved = None
    template = None
    missing_keys = None
    invalid_types = None

    def __new__(
        cls, filled_template, template, solved,
        used_values, missing_keys, invalid_types
    ):
        new_obj = super(TemplateResult, cls).__new__(cls, filled_template)
        new_obj.used_values = used_values
        new_obj.solved = solved
        new_obj.template = template
        new_obj.missing_keys = list(set(missing_keys))
        new_obj.invalid_types = invalid_types
        return new_obj

    def validate(self):
        if not self.solved:
            raise TemplateUnsolved(
                self.template,
                self.missing_keys,
                self.invalid_types
            )


class TemplatesResultDict(dict):
    """Holds and wrap TemplateResults for easy bug report."""

    def __init__(self, in_data, key=None, parent=None, strict=None):
        super(TemplatesResultDict, self).__init__()
        for _key, _value in in_data.items():
            if isinstance(_value, dict):
                _value = self.__class__(_value, _key, self)
            self[_key] = _value

        self.key = key
        self.parent = parent
        self.strict = strict
        if self.parent is None and strict is None:
            self.strict = True

    def __getitem__(self, key):
        if key not in self.keys():
            hier = self.hierarchy()
            hier.append(key)
            raise TemplateMissingKey(hier)

        value = super(TemplatesResultDict, self).__getitem__(key)
        if isinstance(value, self.__class__):
            return value

        # Raise exception when expected solved templates and it is not.
        if self.raise_on_unsolved and hasattr(value, "validate"):
            value.validate()
        return value

    @property
    def raise_on_unsolved(self):
        """To affect this change `strict` attribute."""
        if self.strict is not None:
            return self.strict
        return self.parent.raise_on_unsolved

    def hierarchy(self):
        """Return dictionary keys one by one to root parent."""
        if self.parent is None:
            return []

        hier_keys = []
        par_hier = self.parent.hierarchy()
        if par_hier:
            hier_keys.extend(par_hier)
        hier_keys.append(self.key)

        return hier_keys

    @property
    def missing_keys(self):
        """Return missing keys of all children templates."""
        missing_keys = set()
        for value in self.values():
            missing_keys |= value.missing_keys
        return missing_keys

    @property
    def invalid_types(self):
        """Return invalid types of all children templates."""
        invalid_types = {}
        for value in self.values():
            invalid_types = merge_dict(invalid_types, value.invalid_types)
        return invalid_types

    @property
    def used_values(self):
        """Return used values for all children templates."""
        used_values = {}
        for value in self.values():
            used_values = merge_dict(used_values, value.used_values)
        return used_values

    def get_solved(self):
        """Get only solved key from templates."""
        result = {}
        for key, value in self.items():
            if isinstance(value, self.__class__):
                value = value.get_solved()
                if not value:
                    continue
                result[key] = value

            elif (
                not hasattr(value, "solved") or
                value.solved
            ):
                result[key] = value
        return self.__class__(result, key=self.key, parent=self.parent)


class TemplatePartResult:
    """Result to store result of template parts."""
    def __init__(self, optional=False):
        # Missing keys or invalid value types of required keys
        self._missing_keys = set()
        self._invalid_types = {}
        # Missing keys or invalid value types of optional keys
        self._missing_optional_keys = set()
        self._invalid_optional_types = {}

        # Used values stored by key with origin type
        #   - key without any padding or key modifiers
        #   - value from filling data
        #   Example: {"version": 1}
        self._used_values = {}
        # Used values stored by key with all modifirs
        #   - value is already formatted string
        #   Example: {"version:0>3": "001"}
        self._realy_used_values = {}
        # Concatenated string output after formatting
        self._output = ""
        # Is this result from optional part
        self._optional = True

    def add_output(self, other):
        if isinstance(other, six.string_types):
            self._output += other

        elif isinstance(other, TemplatePartResult):
            self._output += other.output

            self._missing_keys |= other.missing_keys
            self._missing_optional_keys |= other.missing_optional_keys

            self._invalid_types.update(other.invalid_types)
            self._invalid_optional_types.update(other.invalid_optional_types)

            if other.optional and not other.solved:
                return
            self._used_values.update(other.used_values)
            self._realy_used_values.update(other.realy_used_values)

        else:
            raise TypeError("Cannot add data from \"{}\" to \"{}\"".format(
                str(type(other)), self.__class__.__name__)
            )

    @property
    def solved(self):
        if self.optional:
            if (
                len(self.missing_optional_keys) > 0
                or len(self.invalid_optional_types) > 0
            ):
                return False
        return (
            len(self.missing_keys) == 0
            and len(self.invalid_types) == 0
        )

    @property
    def optional(self):
        return self._optional

    @property
    def output(self):
        return self._output

    @property
    def missing_keys(self):
        return self._missing_keys

    @property
    def missing_optional_keys(self):
        return self._missing_optional_keys

    @property
    def invalid_types(self):
        return self._invalid_types

    @property
    def invalid_optional_types(self):
        return self._invalid_optional_types

    @property
    def realy_used_values(self):
        return self._realy_used_values

    @property
    def used_values(self):
        return self._used_values

    @staticmethod
    def split_keys_to_subdicts(values):
        output = {}
        for key, value in values.items():
            key_padding = list(KEY_PADDING_PATTERN.findall(key))
            if key_padding:
                key = key_padding[0]
            key_subdict = list(SUB_DICT_PATTERN.findall(key))
            data = output
            last_key = key_subdict.pop(-1)
            for subkey in key_subdict:
                if subkey not in data:
                    data[subkey] = {}
                data = data[subkey]
            data[last_key] = value
        return output

    def get_clean_used_values(self):
        new_used_values = {}
        for key, value in self.used_values.items():
            if isinstance(value, FormatObject):
                value = str(value)
            new_used_values[key] = value

        return self.split_keys_to_subdicts(new_used_values)

    def add_realy_used_value(self, key, value):
        self._realy_used_values[key] = value

    def add_used_value(self, key, value):
        self._used_values[key] = value

    def add_missing_key(self, key):
        if self._optional:
            self._missing_optional_keys.add(key)
        else:
            self._missing_keys.add(key)

    def add_invalid_type(self, key, value):
        if self._optional:
            self._invalid_optional_types[key] = type(value)
        else:
            self._invalid_types[key] = type(value)


class FormatObject(object):
    """Object that can be used for formatting.

    This is base that is valid for to be used in 'StringTemplate' value.
    """
    def __init__(self):
        self.value = ""

    def __format__(self, *args, **kwargs):
        return self.value.__format__(*args, **kwargs)

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return self.__str__()


class FormattingPart:
    """String with formatting template.

    Containt only single key to format e.g. "{project[name]}".

    Args:
        template(str): String containing the formatting key.
    """
    def __init__(self, template):
        self._template = template

    @property
    def template(self):
        return self._template

    def __repr__(self):
        return "<Format:{}>".format(self._template)

    def __str__(self):
        return self._template

    @staticmethod
    def validate_value_type(value):
        """Check if value can be used for formatting of single key."""
        if isinstance(value, (numbers.Number, FormatObject)):
            return True

        for inh_class in type(value).mro():
            if inh_class in six.string_types:
                return True
        return False

    def format(self, data, result):
        """Format the formattings string.

        Args:
            data(dict): Data that should be used for formatting.
            result(TemplatePartResult): Object where result is stored.
        """
        key = self.template[1:-1]
        if key in result.realy_used_values:
            result.add_output(result.realy_used_values[key])
            return result

        # check if key expects subdictionary keys (e.g. project[name])
        existence_check = key
        key_padding = list(KEY_PADDING_PATTERN.findall(existence_check))
        if key_padding:
            existence_check = key_padding[0]
        key_subdict = list(SUB_DICT_PATTERN.findall(existence_check))

        value = data
        missing_key = False
        invalid_type = False
        used_keys = []
        for sub_key in key_subdict:
            if (
                value is None
                or (hasattr(value, "items") and sub_key not in value)
            ):
                missing_key = True
                used_keys.append(sub_key)
                break

            if not hasattr(value, "items"):
                invalid_type = True
                break

            used_keys.append(sub_key)
            value = value.get(sub_key)

        if missing_key or invalid_type:
            if len(used_keys) == 0:
                invalid_key = key_subdict[0]
            else:
                invalid_key = used_keys[0]
                for idx, sub_key in enumerate(used_keys):
                    if idx == 0:
                        continue
                    invalid_key += "[{0}]".format(sub_key)

            if missing_key:
                result.add_missing_key(invalid_key)

            elif invalid_type:
                result.add_invalid_type(invalid_key, value)

            result.add_output(self.template)
            return result

        if self.validate_value_type(value):
            fill_data = {}
            first_value = True
            for used_key in reversed(used_keys):
                if first_value:
                    first_value = False
                    fill_data[used_key] = value
                else:
                    _fill_data = {used_key: fill_data}
                    fill_data = _fill_data

            formatted_value = self.template.format(**fill_data)
            result.add_realy_used_value(key, formatted_value)
            result.add_used_value(existence_check, formatted_value)
            result.add_output(formatted_value)
            return result

        result.add_invalid_type(key, value)
        result.add_output(self.template)

        return result


class OptionalPart:
    """Template part which contains optional formatting strings.

    If this part can't be filled the result is empty string.

    Args:
        parts(list): Parts of template. Can contain 'str', 'OptionalPart' or
            'FormattingPart'.
    """
    def __init__(self, parts):
        self._parts = parts

    @property
    def parts(self):
        return self._parts

    def __str__(self):
        return "<{}>".format("".join([str(p) for p in self._parts]))

    def __repr__(self):
        return "<Optional:{}>".format("".join([str(p) for p in self._parts]))

    def format(self, data, result):
        new_result = TemplatePartResult(True)
        for part in self._parts:
            if isinstance(part, six.string_types):
                new_result.add_output(part)
            else:
                part.format(data, new_result)

        if new_result.solved:
            result.add_output(new_result)
        return result
