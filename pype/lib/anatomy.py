import os
import re
import json
import copy
import platform
import collections
import numbers
try:
    StringType = basestring
except NameError:
    StringType = str

from . import config
from .log import PypeLogger

try:
    import ruamel.yaml as yaml
except ImportError:
    print("yaml module wasn't found, skipping anatomy")
else:
    directory = os.path.join(
        os.environ.get("PYPE_ENV", ""), "Lib", "site-packages", "ruamel"
    )
    file_path = os.path.join(directory, "__init__.py")
    if os.path.exists(directory) and not os.path.exists(file_path):
        print(
            "{0} found but not {1}. Patching ruamel.yaml...".format(
                directory, file_path
            )
        )
        open(file_path, "a").close()

log = PypeLogger().get_logger(__name__)


def overrides_dir_path():
    value = os.environ.get("PYPE_PROJECT_CONFIGS")
    if value:
        value = os.path.normpath(value)
    return value


def project_overrides_dir_path(project_name):
    return os.path.join(
        overrides_dir_path(),
        project_name
    )


def project_anatomy_overrides_dir_path(project_name):
    return os.path.join(
        project_overrides_dir_path(project_name),
        "anatomy"
    )


def default_anatomy_dir_path():
    return os.path.join(
        os.environ["PYPE_CONFIG"],
        "anatomy"
    )


class RootCombinationError(Exception):
    """This exception is raised when templates has combined root types."""

    def __init__(self, roots):
        joined_roots = ", ".join(
            ["\"{}\"".format(_root) for _root in roots]
        )
        msg = (
            "Combination of root with and"
            " without root name in Templates. {}"
        ).format(joined_roots)

        return super(self.__class__, self).__init__(msg)


class Anatomy:
    """Anatomy module helps to keep project settings.

    Wraps key project specifications, Templates and Roots.

    Args:
        project_name (str): Project name to look on overrides.
        keep_updated (bool): Project name is updated by AVALON_PROJECT environ.
    """

    root_key_regex = re.compile(r"{(root?[^}]+)}")
    root_name_regex = re.compile(r"root\[([^]]+)\]")

    def __init__(self, project_name=None, keep_updated=False):
        if not project_name:
            project_name = os.environ.get("AVALON_PROJECT")

        self.project_name = project_name
        self.keep_updated = keep_updated

        self._templates_obj = Templates(parent=self)
        self._roots_obj = Roots(parent=self)

    def reset(self):
        """Reset values of cached data in templates and roots objects."""
        self.templates_obj.reset()
        self.roots_obj.reset()

    @property
    def templates(self):
        """Wrap property `templates` of Anatomy's Templates instance."""
        return self._templates_obj.templates

    @property
    def templates_obj(self):
        """Return `Templates` object of current Anatomy instance."""
        return self._templates_obj

    def format(self, *args, **kwargs):
        """Wrap `format` method of Anatomy's `templates_obj`."""
        return self._templates_obj.format(*args, **kwargs)

    def format_all(self, *args, **kwargs):
        """Wrap `format_all` method of Anatomy's `templates_obj`."""
        return self._templates_obj.format_all(*args, **kwargs)

    @property
    def roots(self):
        """Wrap `roots` property of Anatomy's `roots_obj`."""
        return self._roots_obj.roots

    @property
    def roots_obj(self):
        """Return `Roots` object of current Anatomy instance."""
        return self._roots_obj

    def root_environments(self):
        """Return PYPE_ROOT_* environments for current project in dict."""
        return self._roots_obj.root_environments()

    def find_root_template_from_path(self, *args, **kwargs):
        """Wrapper for Roots `find_root_template_from_path`."""
        return self.roots_obj.find_root_template_from_path(*args, **kwargs)

    def path_remapper(self, *args, **kwargs):
        """Wrapper for Roots `path_remapper`."""
        return self.roots_obj.path_remapper(*args, **kwargs)

    def all_root_paths(self):
        """Wrapper for Roots `all_root_paths`."""
        return self.roots_obj.all_root_paths()

    def set_root_environments(self):
        """Set PYPE_ROOT_* environments for current project."""
        self._roots_obj.set_root_environments()

    def root_names(self):
        """Return root names for current project."""
        return self.root_names_from_templates(self.templates)

    def _root_keys_from_templates(self, data):
        """Extract root key from templates in data.

        Args:
            data (dict): Data that may contain templates as string.

        Return:
            set: Set of all root names from templates as strings.

        Output example: `{"root[work]", "root[publish]"}`
        """

        output = set()
        if isinstance(data, dict):
            for value in data.values():
                for root in self._root_keys_from_templates(value):
                    output.add(root)

        elif isinstance(data, str):
            for group in re.findall(self.root_key_regex, data):
                output.add(group)

        return output

    def root_value_for_template(self, template):
        """Returns value of root key from template."""
        root_templates = []
        for group in re.findall(self.root_key_regex, template):
            root_templates.append(group)

        if not root_templates:
            return None

        return root_templates[0].format(**{"root": self.roots})

    def root_names_from_templates(self, templates):
        """Extract root names form anatomy templates.

        Returns None if values in templates contain only "{root}".
        Empty list is returned if there is no "root" in templates.
        Else returns all root names from templates in list.

        RootCombinationError is raised when templates contain both root types,
        basic "{root}" and with root name specification "{root[work]}".

        Args:
            templates (dict): Anatomy templates where roots are not filled.

        Return:
            list/None: List of all root names from templates as strings when
            multiroot setup is used, otherwise None is returned.
        """
        roots = list(self._root_keys_from_templates(templates))
        # Return empty list if no roots found in templates
        if not roots:
            return roots

        # Raise exception when root keys have roots with and without root name.
        # Invalid output example: ["root", "root[project]", "root[render]"]
        if len(roots) > 1 and "root" in roots:
            raise RootCombinationError(roots)

        # Return None if "root" without root name in templates
        if len(roots) == 1 and roots[0] == "root":
            return None

        names = set()
        for root in roots:
            for group in re.findall(self.root_name_regex, root):
                names.add(group)
        return list(names)

    def fill_root(self, template_path):
        """Fill template path where is only "root" key unfilled.

        Args:
            template_path (str): Path with "root" key in.
                Example path: "{root}/projects/MyProject/Shot01/Lighting/..."

        Return:
            str: formatted path
        """
        # NOTE does not care if there are different keys than "root"
        return template_path.format(**{"root": self.roots})


class TemplateMissingKey(Exception):
    """Exception for cases when key does not exist in Anatomy."""

    msg = "Anatomy key does not exist: `anatomy{0}`."

    def __init__(self, parents):
        parent_join = "".join(["[\"{0}\"]".format(key) for key in parents])
        super(TemplateMissingKey, self).__init__(
            self.msg.format(parent_join)
        )


class TemplateUnsolved(Exception):
    """Exception for unsolved template when strict is set to True."""

    msg = "Anatomy template \"{0}\" is unsolved.{1}{2}"
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


class TemplateResult(str):
    """Result (formatted template) of anatomy with most of information in.

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

    def __new__(
        cls, filled_template, template, solved, rootless_path,
        used_values, missing_keys, invalid_types
    ):
        new_obj = super(TemplateResult, cls).__new__(cls, filled_template)
        new_obj.used_values = used_values
        new_obj.solved = solved
        new_obj.template = template
        new_obj.rootless = rootless_path
        new_obj.missing_keys = list(set(missing_keys))
        _invalid_types = {}
        for invalid_type in invalid_types:
            for key, val in invalid_type.items():
                if key in _invalid_types:
                    continue
                _invalid_types[key] = val
        new_obj.invalid_types = _invalid_types
        return new_obj


class TemplatesDict(dict):
    """Holds and wrap TemplateResults for easy bug report."""

    def __init__(self, in_data, key=None, parent=None, strict=None):
        super(TemplatesDict, self).__init__()
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
        # Raise error about missing key in anatomy.yaml
        if key not in self.keys():
            hier = self.hierarchy()
            hier.append(key)
            raise TemplateMissingKey(hier)

        value = super(TemplatesDict, self).__getitem__(key)
        if isinstance(value, self.__class__):
            return value

        # Raise exception when expected solved templates and it is not.
        if (
            self.raise_on_unsolved
            and (hasattr(value, "solved") and not value.solved)
        ):
            raise TemplateUnsolved(
                value.template, value.missing_keys, value.invalid_types
            )
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
        missing_keys = []
        for value in self.values():
            missing_keys.extend(value.missing_keys)
        return list(set(missing_keys))

    @property
    def invalid_types(self):
        """Return invalid types of all children templates."""
        invalid_types = {}
        for value in self.values():
            for invalid_type in value.invalid_types:
                _invalid_types = {}
                for key, val in invalid_type.items():
                    if key in invalid_types:
                        continue
                    _invalid_types[key] = val
                invalid_types = config.update_dict(
                    invalid_types, _invalid_types
                )
        return invalid_types

    @property
    def used_values(self):
        """Return used values for all children templates."""
        used_values = {}
        for value in self.values():
            used_values = config.update_dict(used_values, value.used_values)
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


class Templates:
    key_pattern = re.compile(r"(\{.*?[^{0]*\})")
    key_padding_pattern = re.compile(r"([^:]+)\S+[><]\S+")
    sub_dict_pattern = re.compile(r"([^\[\]]+)")
    optional_pattern = re.compile(r"(<.*?[^{0]*>)[^0-9]*?")

    inner_key_pattern = re.compile(r"(\{@.*?[^{}0]*\})")
    inner_key_name_pattern = re.compile(r"\{@(.*?[^{}0]*)\}")

    templates_file_name = "default.yaml"

    def __init__(
        self, project_name=None, keep_updated=False, roots=None, parent=None
    ):
        self._keep_updated = keep_updated
        self._project_name = project_name
        self._roots = roots
        self.parent = parent
        if parent is None and project_name is None:
            log.warning((
                "It is expected to enter project_name if Templates are created"
                " out of Anatomy."
            ))

        self.loaded_project = None
        self._templates = None

    def __getitem__(self, key):
        return self.templates[key]

    def get(self, key, default=None):
        return self.templates.get(key, default)

    def reset(self):
        self._templates = None

    @property
    def project_name(self):
        if self.parent:
            return self.parent.project_name
        return self._project_name

    @property
    def keep_updated(self):
        if self.parent:
            return self.parent.keep_updated
        return self._keep_updated

    @property
    def roots(self):
        if self.parent:
            return self.parent.roots
        return self._roots

    @property
    def templates(self):
        if self.parent is None and self.keep_updated:
            project = os.environ.get("AVALON_PROJECT", None)
            if project is not None and project != self.project_name:
                self._project_name = project

        if self.project_name != self.loaded_project:
            self._templates = None

        if self._templates is None:
            self._templates = self._discover()
            self.loaded_project = self.project_name
        return self._templates

    @staticmethod
    def default_templates_raw():
        """Return default templates raw data."""
        path = os.path.join(
            default_anatomy_dir_path(),
            Templates.templates_file_name
        )
        with open(path, "r") as stream:
            # QUESTION Should we not raise exception if file is invalid?
            default_templates = yaml.load(
                stream, Loader=yaml.loader.Loader
            )
        return default_templates

    @staticmethod
    def default_templates():
        """Return default templates data with solved inner keys."""
        return Templates.solve_template_inner_links(
            Templates.default_templates_raw()
        )

    @staticmethod
    def project_overrides_path(project_name):
        return os.path.join(
            project_anatomy_overrides_dir_path(project_name),
            Templates.templates_file_name
        )

    def _project_overrides_path(self):
        """Returns path to project's overide template file."""
        return Templates.project_overrides_path(self.project_name)

    @staticmethod
    def save_project_overrides(project_name, templates=None, override=False):
        """Save templates values into projects overrides.

        Creates or replace "default.yaml" file in project overrides.

        Args:
            project_name (str): Project name for which overrides will be saved.
            templates (dict, optional): Templates values to save into
                project's overrides. Filled with `default_templates_raw` when
                set to None.
            override (bool): Allows to override already existing templates
                file. This option is set to False by default.
        """
        if templates is None:
            templates = Templates.default_templates_raw()

        yaml_path = Templates.project_overrides_path(project_name)
        if os.path.exists(yaml_path) and not override:
            log.warning((
                "Template overrides for project \"{}\" already exists."
            ).format(project_name))
            return

        yaml_dir_path = os.path.dirname(yaml_path)
        if not os.path.exists(yaml_dir_path):
            log.debug(
                "Creating Anatomy folder: \"{}\"".format(yaml_dir_path)
            )
            os.makedirs(yaml_dir_path)

        yaml_obj = yaml.YAML()
        yaml_obj.indent(mapping=4, sequence=4, offset=4)
        with open(yaml_path, "w") as yaml_file:
            yaml_obj.dump(templates, yaml_file)

    def _discover(self):
        """ Loads anatomy templates from yaml.
        Default templates are loaded if project is not set or project does
        not have set it's own.
        TODO: create templates if not exist.

        Returns:
            TemplatesDict: Contain templates data for current project of
                default templates.
        """

        if self.project_name is not None:
            project_templates_path = self._project_overrides_path()
            if os.path.exists(project_templates_path):
                # QUESTION Should we not raise exception if file is invalid?
                with open(project_templates_path, "r") as stream:
                    proj_templates = yaml.load(
                        stream, Loader=yaml.loader.Loader
                    )
                return Templates.solve_template_inner_links(proj_templates)

            else:
                # QUESTION create project specific if not found?
                log.warning((
                    "Project \"{0}\" does not have his own templates."
                    " Trying to use default."
                ).format(self.project_name))

        return self.default_templates()

    @classmethod
    def replace_inner_keys(cls, matches, value, key_values, key):
        """Replacement of inner keys in template values."""
        for match in matches:
            anatomy_sub_keys = (
                cls.inner_key_name_pattern.findall(match)
            )
            if key in anatomy_sub_keys:
                raise ValueError((
                    "Unsolvable recursion in inner keys, "
                    "key: \"{}\" is in his own value."
                    " Can't determine source, please check Anatomy templates."
                ).format(key))

            for anatomy_sub_key in anatomy_sub_keys:
                replace_value = key_values.get(anatomy_sub_key)
                if replace_value is None:
                    raise KeyError((
                        "Anatomy templates can't be filled."
                        " Anatomy key `{0}` has"
                        " invalid inner key `{1}`."
                    ).format(key, anatomy_sub_key))

                valid = isinstance(replace_value, (numbers.Number, StringType))
                if not valid:
                    raise ValueError((
                        "Anatomy templates can't be filled."
                        " Anatomy key `{0}` has"
                        " invalid inner key `{1}`"
                        " with value `{2}`."
                    ).format(key, anatomy_sub_key, str(replace_value)))

                value = value.replace(match, str(replace_value))

        return value

    @classmethod
    def prepare_inner_keys(cls, key_values):
        """Check values of inner keys.

        Check if inner key exist in template group and has valid value.
        It is also required to avoid infinite loop with unsolvable recursion
        when first inner key's value refers to second inner key's value where
        first is used.
        """
        keys_to_solve = set(key_values.keys())
        while True:
            found = False
            for key in tuple(keys_to_solve):
                value = key_values[key]

                if isinstance(value, StringType):
                    matches = cls.inner_key_pattern.findall(value)
                    if not matches:
                        keys_to_solve.remove(key)
                        continue

                    found = True
                    key_values[key] = cls.replace_inner_keys(
                        matches, value, key_values, key
                    )
                    continue

                elif not isinstance(value, dict):
                    keys_to_solve.remove(key)
                    continue

                subdict_found = False
                for _key, _value in tuple(value.items()):
                    matches = cls.inner_key_pattern.findall(_value)
                    if not matches:
                        continue

                    subdict_found = True
                    found = True
                    key_values[key][_key] = cls.replace_inner_keys(
                        matches, _value, key_values,
                        "{}.{}".format(key, _key)
                    )

                if not subdict_found:
                    keys_to_solve.remove(key)

            if not found:
                break

        return key_values

    @classmethod
    def solve_template_inner_links(cls, templates):
        """Solve templates inner keys identified by "{@*}".

        Process is split into 2 parts.
        First is collecting all global keys (keys in top hierarchy where value
        is not dictionary). All global keys are set for all group keys (keys
        in top hierarchy where value is dictionary). Value of a key is not
        overriden in group if already contain value for the key.

        In second part all keys with "at" symbol in value are replaced with
        value of the key afterward "at" symbol from the group.

        Args:
            templates (dict): Raw templates data.

        Example:
            templates::
                key_1: "value_1",
                key_2: "{@key_1}/{filling_key}"

                group_1:
                    key_3: "value_3/{@key_2}"

                group_2:
                    key_2": "value_2"
                    key_4": "value_4/{@key_2}"

            output::
                key_1: "value_1"
                key_2: "value_1/{filling_key}"

                group_1: {
                    key_1: "value_1"
                    key_2: "value_1/{filling_key}"
                    key_3: "value_3/value_1/{filling_key}"

                group_2: {
                    key_1: "value_1"
                    key_2: "value_2"
                    key_4: "value_3/value_2"
        """
        default_key_values = {}
        for key, value in tuple(templates.items()):
            if isinstance(value, dict):
                continue
            default_key_values[key] = templates.pop(key)

        keys_by_subkey = {}
        for sub_key, sub_value in templates.items():
            key_values = {}
            key_values.update(default_key_values)
            key_values.update(sub_value)
            keys_by_subkey[sub_key] = cls.prepare_inner_keys(key_values)

        default_keys_by_subkeys = cls.prepare_inner_keys(default_key_values)

        for key, value in default_keys_by_subkeys.items():
            keys_by_subkey[key] = value

        return keys_by_subkey

    def _filter_optional(self, template, data):
        """Filter invalid optional keys.

        Invalid keys may be missing keys of with invalid value DataType.

        Args:
            template (str): Anatomy template which will be formatted.
            data (dict): Containing keys to be filled into template.

        Result:
            tuple: Contain origin template without missing optional keys and
                withoud optional keys identificator ("<" and ">"), information
                about missing optional keys and invalid types of optional keys.

        """

        # Remove optional missing keys
        missing_keys = []
        invalid_types = []
        for optional_group in self.optional_pattern.findall(template):
            _missing_keys = []
            _invalid_types = []
            for optional_key in self.key_pattern.findall(optional_group):
                key = str(optional_key[1:-1])
                key_padding = list(
                    self.key_padding_pattern.findall(key)
                )
                if key_padding:
                    key = key_padding[0]

                validation_result = self._validate_data_key(
                    key, data
                )
                missing_key = validation_result["missing_key"]
                invalid_type = validation_result["invalid_type"]

                valid = True
                if missing_key is not None:
                    _missing_keys.append(missing_key)
                    valid = False

                if invalid_type is not None:
                    _invalid_types.append(invalid_type)
                    valid = False

                if valid:
                    try:
                        optional_key.format(**data)
                    except KeyError:
                        _missing_keys.append(key)
                        valid = False

            valid = len(_invalid_types) == 0 and len(_missing_keys) == 0
            missing_keys.extend(_missing_keys)
            invalid_types.extend(_invalid_types)
            replacement = ""
            if valid:
                replacement = optional_group[1:-1]

            template = template.replace(optional_group, replacement)
        return (template, missing_keys, invalid_types)

    def _validate_data_key(self, key, data):
        """Check and prepare missing keys and invalid types of template."""
        result = {
            "missing_key": None,
            "invalid_type": None
        }

        # check if key expects subdictionary keys (e.g. project[name])
        key_subdict = list(self.sub_dict_pattern.findall(key))
        used_keys = []
        if len(key_subdict) <= 1:
            if key not in data:
                result["missing_key"] = key
                return result

            used_keys.append(key)
            value = data[key]

        else:
            value = data
            missing_key = False
            invalid_type = False
            for sub_key in key_subdict:
                if (
                    value is None
                    or (hasattr(value, "items") and sub_key not in value)
                ):
                    missing_key = True
                    used_keys.append(sub_key)
                    break

                elif not hasattr(value, "items"):
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
                    result["missing_key"] = invalid_key

                elif invalid_type:
                    result["invalid_type"] = {invalid_key: type(value)}

                return result

        if isinstance(value, (numbers.Number, Roots, RootItem)):
            return result

        for inh_class in type(value).mro():
            if inh_class == StringType:
                return result

        result["missing_key"] = key
        result["invalid_type"] = {key: type(value)}
        return result

    def _merge_used_values(self, current_used, keys, value):
        key = keys[0]
        _keys = keys[1:]
        if len(_keys) == 0:
            current_used[key] = value
        else:
            next_dict = {}
            if key in current_used:
                next_dict = current_used[key]
            current_used[key] = self._merge_used_values(
                next_dict, _keys, value
            )
        return current_used

    def _dict_to_subkeys_list(self, subdict, pre_keys=None):
        if pre_keys is None:
            pre_keys = []
        output = []
        for key in subdict:
            value = subdict[key]
            result = list(pre_keys)
            result.append(key)
            if isinstance(value, dict):
                for item in self._dict_to_subkeys_list(value, result):
                    output.append(item)
            else:
                output.append(result)
        return output

    def _keys_to_dicts(self, key_list, value):
        if not key_list:
            return None
        if len(key_list) == 1:
            return {key_list[0]: value}
        return {key_list[0]: self._keys_to_dicts(key_list[1:], value)}

    def _rootless_path(
        self, template, used_values, final_data, missing_keys, invalid_types
    ):
        if (
            "root" not in used_values
            or "root" in missing_keys
            or "{root" not in template
        ):
            return

        for invalid_type in invalid_types:
            if "root" in invalid_type:
                return

        root_keys = self._dict_to_subkeys_list({"root": used_values["root"]})
        if not root_keys:
            return

        roots_dict = {}
        for used_root_keys in root_keys:
            if not used_root_keys:
                continue

            root_key = None
            for key in used_root_keys:
                if root_key is None:
                    root_key = key
                else:
                    root_key += "[{}]".format(key)

            root_key = "{" + root_key + "}"

            roots_dict = config.update_dict(
                roots_dict,
                self._keys_to_dicts(used_root_keys, root_key)
            )

        final_data["root"] = roots_dict["root"]
        return template.format(**final_data)

    def _format(self, orig_template, data):
        """ Figure out with whole formatting.

        Separate advanced keys (*Like '{project[name]}') from string which must
        be formatted separatelly in case of missing or incomplete keys in data.

        Args:
            template (str): Anatomy template which will be formatted.
            data (dict): Containing keys to be filled into template.

        Returns:
            TemplateResult: Filled or partially filled template containing all
                data needed or missing for filling template.
        """
        template, missing_optional, invalid_optional = (
            self._filter_optional(orig_template, data)
        )
        # Remove optional missing keys
        used_values = {}
        invalid_required = []
        missing_required = []
        replace_keys = []
        for group in self.key_pattern.findall(template):
            orig_key = group[1:-1]
            key = str(orig_key)
            key_padding = list(self.key_padding_pattern.findall(key))
            if key_padding:
                key = key_padding[0]

            validation_result = self._validate_data_key(key, data)
            missing_key = validation_result["missing_key"]
            invalid_type = validation_result["invalid_type"]

            if invalid_type is not None:
                invalid_required.append(invalid_type)
                replace_keys.append(key)
                continue

            if missing_key is not None:
                missing_required.append(missing_key)
                replace_keys.append(key)
                continue

            try:
                value = group.format(**data)
                key_subdict = list(self.sub_dict_pattern.findall(key))
                if len(key_subdict) <= 1:
                    used_values[key] = value

                else:
                    used_values = self._merge_used_values(
                        used_values, key_subdict, value
                    )

            except (TypeError, KeyError):
                missing_required.append(key)
                replace_keys.append(key)

        final_data = copy.deepcopy(data)
        for key in replace_keys:
            key_subdict = list(self.sub_dict_pattern.findall(key))
            if len(key_subdict) <= 1:
                final_data[key] = "{" + key + "}"
                continue

            replace_key_dst = "---".join(key_subdict)
            replace_key_dst_curly = "{" + replace_key_dst + "}"
            replace_key_src_curly = "{" + key + "}"
            template = template.replace(
                replace_key_src_curly, replace_key_dst_curly
            )
            final_data[replace_key_dst] = replace_key_src_curly

        solved = len(missing_required) == 0 and len(invalid_required) == 0

        missing_keys = missing_required + missing_optional
        invalid_types = invalid_required + invalid_optional

        filled_template = template.format(**final_data)
        # WARNING `_rootless_path` change values in `final_data` please keep
        # in midn when changing order
        rootless_path = self._rootless_path(
            template, used_values, final_data, missing_keys, invalid_types
        )
        if rootless_path is None:
            rootless_path = filled_template

        result = TemplateResult(
            filled_template, orig_template, solved, rootless_path,
            used_values, missing_keys, invalid_types
        )
        return result

    def solve_dict(self, templates, data):
        """ Solves templates with entered data.

        Args:
            templates (dict): All Anatomy templates which will be formatted.
            data (dict): Containing keys to be filled into template.

        Returns:
            dict: With `TemplateResult` in values containing filled or
                partially filled templates.
        """
        output = collections.defaultdict(dict)
        for key, orig_value in templates.items():
            if isinstance(orig_value, StringType):
                output[key] = self._format(orig_value, data)
                continue

            # Check if orig_value has items attribute (any dict inheritance)
            if not hasattr(orig_value, "items"):
                # TODO we should handle this case
                output[key] = orig_value
                continue

            for s_key, s_value in self.solve_dict(orig_value, data).items():
                output[key][s_key] = s_value

        return output

    def format_all(self, in_data, only_keys=True):
        """ Solves templates based on entered data.

        Args:
            data (dict): Containing keys to be filled into template.
            only_keys (bool, optional): Decides if environ will be used to
                fill templates or only keys in data.

        Returns:
            TemplatesDict: Output `TemplateResult` have `strict` attribute
                set to False so accessing unfilled keys in templates won't
                raise any exceptions.
        """
        output = self.format(in_data, only_keys)
        output.strict = False
        return output

    def format(self, in_data, only_keys=True):
        """ Solves templates based on entered data.

        Args:
            data (dict): Containing keys to be filled into template.
            only_keys (bool, optional): Decides if environ will be used to
                fill templates or only keys in data.

        Returns:
            TemplatesDict: Output `TemplateResult` have `strict` attribute
                set to True so accessing unfilled keys in templates will
                raise exceptions with explaned error.
        """
        # Create a copy of inserted data
        data = copy.deepcopy(in_data)

        # Add environment variable to data
        if only_keys is False:
            for key, val in os.environ.items():
                data["$" + key] = val

        # override root value
        roots = self.roots
        if roots:
            data["root"] = roots
        solved = self.solve_dict(self.templates, data)

        return TemplatesDict(solved)


class RootItem:
    """Represents one item or roots.

    Holds raw data of root item specification. Raw data contain value
    for each platform, but current platform value is used when object
    is used for formatting of template.

    Args:
        root_raw_data (dict): Dictionary containing root values by platform
            names. ["windows", "linux" and "darwin"]
        name (str, optional): Root name which is representing. Used with
            multi root setup otherwise None value is expected.
        parent_keys (list, optional): All dictionary parent keys. Values of
            `parent_keys` are used for get full key which RootItem is
            representing. Used for replacing root value in path with
            formattable key. e.g. parent_keys == ["work"] -> {root[work]}
        parent (object, optional): It is expected to be `Roots` object.
            Value of `parent` won't affect code logic much.
    """

    def __init__(
        self, root_raw_data, name=None, parent_keys=[], parent=None
    ):
        lowered_platform_keys = {}
        for key, value in root_raw_data.items():
            lowered_platform_keys[key.lower()] = value
        self.raw_data = lowered_platform_keys
        self.cleaned_data = self._clean_roots(lowered_platform_keys)
        self.name = name
        self.parent_keys = parent_keys
        self.parent = parent

        self.available_platforms = list(lowered_platform_keys.keys())
        self.value = lowered_platform_keys.get(platform.system().lower())
        self.clean_value = self.clean_root(self.value)

    def __format__(self, *args, **kwargs):
        return self.value.__format__(*args, **kwargs)

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return self.__str__()

    def __getitem__(self, key):
        if isinstance(key, numbers.Number):
            return self.value[key]

        additional_info = ""
        if self.parent and self.parent.project_name:
            additional_info += " for project \"{}\"".format(
                self.parent.project_name
            )

        raise AssertionError(
            "Root key \"{}\" is missing{}.".format(
                key, additional_info
            )
        )

    def full_key(self):
        """Full key value for dictionary formatting in template.

        Returns:
            str: Return full replacement key for formatting. This helps when
                multiple roots are set. In that case e.g. `"root[work]"` is
                returned.
        """
        if not self.name:
            return "root"

        joined_parent_keys = "".join(
            ["[{}]".format(key) for key in self.parent_keys]
        )
        return "root{}".format(joined_parent_keys)

    def clean_path(self, path):
        """Just replace backslashes with forward slashes."""
        return str(path).replace("\\", "/")

    def clean_root(self, root):
        """Makes sure root value does not end with slash."""
        if root:
            root = self.clean_path(root)
            while root.endswith("/"):
                root = root[:-1]
        return root

    def _clean_roots(self, raw_data):
        """Clean all values of raw root item values."""
        cleaned = {}
        for key, value in raw_data.items():
            cleaned[key] = self.clean_root(value)
        return cleaned

    def path_remapper(self, path, dst_platform=None, src_platform=None):
        """Remap path for specific platform.

        Args:
            path (str): Source path which need to be remapped.
            dst_platform (str, optional): Specify destination platform
                for which remapping should happen.
            src_platform (str, optional): Specify source platform. This is
                recommended to not use and keep unset until you really want
                to use specific platform.
            roots (dict/RootItem/None, optional): It is possible to remap
                path with different roots then instance where method was
                called has.

        Returns:
            str/None: When path does not contain known root then
                None is returned else returns remapped path with "{root}"
                or "{root[<name>]}".
        """
        cleaned_path = self.clean_path(path)
        if dst_platform:
            dst_root_clean = self.cleaned_data.get(dst_platform)
            if not dst_root_clean:
                key_part = ""
                full_key = self.full_key()
                if full_key != "root":
                    key_part += "\"{}\" ".format(full_key)

                log.warning(
                    "Root {}miss platform \"{}\" definition.".format(
                        key_part, dst_platform
                    )
                )
                return None

            if cleaned_path.startswith(dst_root_clean):
                return cleaned_path

        if src_platform:
            src_root_clean = self.cleaned_data.get(src_platform)
            if src_root_clean is None:
                log.warning(
                    "Root \"{}\" miss platform \"{}\" definition.".format(
                        self.full_key(), src_platform
                    )
                )
                return None

            if not cleaned_path.startswith(src_root_clean):
                return None

            subpath = cleaned_path[len(src_root_clean):]
            if dst_platform:
                # `dst_root_clean` is used from upper condition
                return dst_root_clean + subpath
            return self.clean_value + subpath

        result, template = self.find_root_template_from_path(path)
        if not result:
            return None

        def parent_dict(keys, value):
            if not keys:
                return value

            key = keys.pop(0)
            return {key: parent_dict(keys, value)}

        if dst_platform:
            format_value = parent_dict(list(self.parent_keys), dst_root_clean)
        else:
            format_value = parent_dict(list(self.parent_keys), self.value)

        return template.format(**{"root": format_value})

    def find_root_template_from_path(self, path):
        """Replaces known root value with formattable key in path.

        All platform values are checked for this replacement.

        Args:
            path (str): Path where root value should be found.

        Returns:
            tuple: Tuple contain 2 values: `success` (bool) and `path` (str).
                When success it True then path should contain replaced root
                value with formattable key.

        Example:
            When input path is::
                "C:/windows/path/root/projects/my_project/file.ext"

            And raw data of item looks like::
                {
                    "windows": "C:/windows/path/root",
                    "linux": "/mount/root"
                }

            Output will be::
                (True, "{root}/projects/my_project/file.ext")

            If any of raw data value wouldn't match path's root output is::
                (False, "C:/windows/path/root/projects/my_project/file.ext")
        """
        result = False
        output = str(path)

        root_paths = list(self.cleaned_data.values())
        mod_path = self.clean_path(path)
        for root_path in root_paths:
            if mod_path.startswith(root_path):
                result = True
                replacement = "{" + self.full_key() + "}"
                output = replacement + mod_path[len(root_path):]
                break

        return (result, output)


class Roots:
    """Object which should be used for formatting "root" key in templates.

    Args:
        project_name (str, optional): Project name to look on overrides.
        keep_updated (bool, optional): Project name is updated by
            AVALON_PROJECT environ.
        parent (object, optional): Expected that parent is Anatomy object.
            When parent is set then values of attributes `project_name` and
            `keep_updated` are ignored and are used parent's values.
    """

    env_prefix = "PYPE_ROOT"
    roots_filename = "roots.json"

    def __init__(
        self, project_name=None, keep_updated=False, parent=None
    ):
        self.loaded_project = None
        self._project_name = project_name
        self._keep_updated = keep_updated

        if parent is None and project_name is None:
            log.warning((
                "It is expected to enter project_name if Roots are created"
                " out of Anatomy."
            ))

        self.parent = parent
        self._roots = None

    def __format__(self, *args, **kwargs):
        return self.roots.__format__(*args, **kwargs)

    def __getitem__(self, key):
        return self.roots[key]

    def reset(self):
        """Reset current roots value."""
        self._roots = None

    def path_remapper(
        self, path, dst_platform=None, src_platform=None, roots=None
    ):
        """Remap path for specific platform.

        Args:
            path (str): Source path which need to be remapped.
            dst_platform (str, optional): Specify destination platform
                for which remapping should happen.
            src_platform (str, optional): Specify source platform. This is
                recommended to not use and keep unset until you really want
                to use specific platform.
            roots (dict/RootItem/None, optional): It is possible to remap
                path with different roots then instance where method was
                called has.

        Returns:
            str/None: When path does not contain known root then
                None is returned else returns remapped path with "{root}"
                or "{root[<name>]}".
        """
        if roots is None:
            roots = self.roots

        if roots is None:
            raise ValueError("Roots are not set. Can't find path.")

        if "{root" in path:
            path = path.format(**{"root": roots})
            # If `dst_platform` is not specified then return else continue.
            if not dst_platform:
                return path

        if isinstance(roots, RootItem):
            return roots.path_remapper(path, dst_platform, src_platform)

        for _root in roots.values():
            result = self.path_remapper(
                path, dst_platform, src_platform, _root
            )
            if result is not None:
                return result

    def find_root_template_from_path(self, path, roots=None):
        """Find root value in entered path and replace it with formatting key.

        Args:
            path (str): Source path where root will be searched.
            roots (Roots/dict, optional): It is possible to use different
                roots than instance where method was triggered has.

        Returns:
            tuple: Output contains tuple with bool representing success as
                first value and path with or without replaced root with
                formatting key as second value.

        Raises:
            ValueError: When roots are not entered and can't be loaded.
        """
        if roots is None:
            log.debug(
                "Looking for matching root in path \"{}\".".format(path)
            )
            roots = self.roots

        if roots is None:
            raise ValueError("Roots are not set. Can't find path.")

        if isinstance(roots, RootItem):
            return roots.find_root_template_from_path(path)

        for root_name, _root in roots.items():
            success, result = self.find_root_template_from_path(path, _root)
            if success:
                log.info("Found match in root \"{}\".".format(root_name))
                return success, result

        log.warning("No matching root was found in current setting.")
        return (False, path)

    def set_root_environments(self):
        """Set root environments for current project."""
        for key, value in self.root_environments().items():
            os.environ[key] = value

    def root_environments(self):
        """Use root keys to create unique keys for environment variables.

        Concatenates prefix "PYPE_ROOT" with root keys to create unique keys.

        Returns:
            dict: Result is `{(str): (str)}` dicitonary where key represents
                unique key concatenated by keys and value is root value of
                current platform root.

        Example:
            With raw root values::
                "work": {
                    "windows": "P:/projects/work",
                    "linux": "/mnt/share/projects/work",
                    "darwin": "/darwin/path/work"
                },
                "publish": {
                    "windows": "P:/projects/publish",
                    "linux": "/mnt/share/projects/publish",
                    "darwin": "/darwin/path/publish"
                }

            Result on windows platform::
                {
                    "PYPE_ROOT_WORK": "P:/projects/work",
                    "PYPE_ROOT_PUBLISH": "P:/projects/publish"
                }

            Short example when multiroot is not used::
                {
                    "PYPE_ROOT": "P:/projects"
                }
        """
        return self._root_environments()

    def all_root_paths(self, roots=None):
        """Return all paths for all roots of all platforms."""
        if roots is None:
            roots = self.roots

        output = []
        if isinstance(roots, RootItem):
            for value in roots.raw_data.values():
                output.append(value)
            return output

        for _roots in roots.values():
            output.extend(self.all_root_paths(_roots))
        return output

    def _root_environments(self, keys=[], roots=None):
        if roots is None:
            roots = self.roots

        if isinstance(roots, RootItem):
            key_items = [self.env_prefix]
            for _key in keys:
                key_items.append(_key.upper())
            key = "_".join(key_items)
            return {key: roots.value}

        output = {}
        for _key, _value in roots.items():
            _keys = list(keys)
            _keys.append(_key)
            output.update(self._root_environments(_keys, _value))
        return output

    @property
    def project_name(self):
        """Return project name which will be used for loading root values."""
        if self.parent:
            return self.parent.project_name
        return self._project_name

    @property
    def keep_updated(self):
        """Keep updated property helps to keep roots updated.

        Returns:
            bool: Return True when roots should be updated for project set
                in "AVALON_PROJECT" environment variable.
        """
        if self.parent:
            return self.parent.keep_updated
        return self._keep_updated

    @staticmethod
    def project_overrides_path(project_name):
        """Returns path to project overrides roots file."""
        project_config_items = [
            project_anatomy_overrides_dir_path(project_name),
            Roots.roots_filename
        ]
        return os.path.sep.join(project_config_items)

    def _project_overrides_path(self):
        return Roots.project_overrides_path(self.project_name)

    @property
    def roots(self):
        """Property for filling "root" key in templates.

        This property returns roots for current project or default root values.
        Warning:
            Default roots value may cause issues when project use different
            roots settings. That may happend when project use multiroot
            templates but default roots miss their keys.
        """
        if self.parent is None and self.keep_updated:
            project_name = os.environ.get("AVALON_PROJECT")
            if self.project_name != project_name:
                self._project_name = project_name

        if self.project_name != self.loaded_project:
            self._roots = None

        if self._roots is None:
            self._roots = self._discover()
            self.loaded_project = self.project_name
            # Backwards compatibility
            if self._roots is None:
                self._roots = Roots.default_roots(self)
        return self._roots

    @staticmethod
    def default_roots_raw():
        """Loads raw default roots data from roots.json."""
        default_roots_path = os.path.normpath(os.path.join(
            default_anatomy_dir_path(),
            Roots.roots_filename
        ))
        with open(default_roots_path, "r") as default_roots_file:
            raw_default_roots = json.load(default_roots_file)

        return raw_default_roots

    @staticmethod
    def default_roots(parent=None):
        """Returns parsed default roots."""
        return Roots._parse_dict(Roots.default_roots_raw())

    def _discover(self):
        """ Loads current project's roots or default.

        Default roots are loaded if project override's does not contain roots.

        Returns:
            `RootItem` or `dict` with multiple `RootItem`s when multiroot
            setting is used.
        """

        # Return default roots if project is not set
        if self.project_name is None:
            return Roots.default_roots(self)

        # Return project specific roots
        project_roots_path = self._project_overrides_path()

        # If path does not exist we assume it is older project without roots
        if not os.path.exists(project_roots_path):
            return None

        with open(project_roots_path, "r") as project_roots_file:
            raw_project_roots = json.load(project_roots_file)

        return self._parse_dict(raw_project_roots, parent=self)

    @staticmethod
    def _parse_dict(data, key=None, parent_keys=[], parent=None):
        """Parse roots raw data into RootItem or dictionary with RootItems.

        Converting raw roots data to `RootItem` helps to handle platform keys.
        This method is recursive to be able handle multiroot setup and
        is static to be able to load default roots without creating new object.

        Args:
            data (dict): Should contain raw roots data to be parsed.
            key (str, optional): Current root key. Set by recursion.
            parent_keys (list): Parent dictionary keys. Set by recursion.
            parent (Roots, optional): Parent object set in `RootItem`
                helps to keep RootItem instance updated with `Roots` object.

        Returns:
            `RootItem` or `dict` with multiple `RootItem`s when multiroot
            setting is used.
        """
        is_last = False
        for value in data.values():
            if isinstance(value, StringType):
                is_last = True
                break

        if is_last:
            return RootItem(data, key, parent_keys, parent=parent)

        output = {}
        for key, value in data.items():
            _parent_keys = list(parent_keys)
            _parent_keys.append(key)
            output[key] = Roots._parse_dict(value, key, _parent_keys, parent)
        return output

    @staticmethod
    def save_project_overrides(project_name, roots_data=None, override=False):
        """Save root values into projects overrides.

        Creates or replace "roots.json" file in project overrides.

        Args:
            project_name (str): Project name for which overrides will be saved.
            roots_data (dict, optional): Root values to save into
                project's overrides. Filled with `default_roots_raw` when
                set to None.
            override (bool): Allows to override already existing roots file.
                This option is set to False by default.

        Example:
            `roots_data` should contain platform specific keys::
                {
                    "windows": "P:/projects",
                    "linux": "/mnt/share/projects",
                    "darwin": "/Volumes/projects"
                }
        """

        if roots_data is None:
            roots_data = Roots.default_roots_raw()

        json_path = Roots.project_overrides_path(project_name)
        if os.path.exists(json_path) and not override:
            log.warning((
                "Roots overrides for project \"{}\" already exists."
            ).format(project_name))
            return

        json_dir_path = os.path.dirname(json_path)
        if not os.path.exists(json_dir_path):
            log.debug(
                "Creating Anatomy folder: \"{}\"".format(json_dir_path)
            )
            os.makedirs(json_dir_path)

        with open(json_path, "w") as json_file:
            json.dump(roots_data, json_file)
