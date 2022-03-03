import os
import re
import copy
import platform
import collections
import numbers

from openpype.settings.lib import (
    get_default_anatomy_settings,
    get_anatomy_settings
)
from .path_templates import (
    TemplateUnsolved,
    TemplateResult,
    TemplatesDict,
    FormatObject,
)
from .log import PypeLogger

log = PypeLogger().get_logger(__name__)

try:
    StringType = basestring
except NameError:
    StringType = str


class ProjectNotSet(Exception):
    """Exception raised when is created Anatomy without project name."""


class RootCombinationError(Exception):
    """This exception is raised when templates has combined root types."""

    def __init__(self, roots):
        joined_roots = ", ".join(
            ["\"{}\"".format(_root) for _root in roots]
        )
        # TODO better error message
        msg = (
            "Combination of root with and"
            " without root name in AnatomyTemplates. {}"
        ).format(joined_roots)

        super(RootCombinationError, self).__init__(msg)


class Anatomy:
    """Anatomy module helps to keep project settings.

    Wraps key project specifications, AnatomyTemplates and Roots.

    Args:
        project_name (str): Project name to look on overrides.
    """

    root_key_regex = re.compile(r"{(root?[^}]+)}")
    root_name_regex = re.compile(r"root\[([^]]+)\]")

    def __init__(self, project_name=None, site_name=None):
        if not project_name:
            project_name = os.environ.get("AVALON_PROJECT")

        if not project_name:
            raise ProjectNotSet((
                "Implementation bug: Project name is not set. Anatomy requires"
                " to load data for specific project."
            ))

        self.project_name = project_name

        self._data = self._prepare_anatomy_data(
            get_anatomy_settings(project_name, site_name)
        )
        self._site_name = site_name
        self._templates_obj = AnatomyTemplates(self)
        self._roots_obj = Roots(self)

    # Anatomy used as dictionary
    # - implemented only getters returning copy
    def __getitem__(self, key):
        return copy.deepcopy(self._data[key])

    def get(self, key, default=None):
        return copy.deepcopy(self._data).get(key, default)

    def keys(self):
        return copy.deepcopy(self._data).keys()

    def values(self):
        return copy.deepcopy(self._data).values()

    def items(self):
        return copy.deepcopy(self._data).items()

    @staticmethod
    def default_data():
        """Default project anatomy data.

        Always return fresh loaded data. May be used as data for new project.

        Not used inside Anatomy itself.
        """
        return get_default_anatomy_settings(clear_metadata=False)

    @staticmethod
    def _prepare_anatomy_data(anatomy_data):
        """Prepare anatomy data for further processing.

        Method added to replace `{task}` with `{task[name]}` in templates.
        """
        templates_data = anatomy_data.get("templates")
        if templates_data:
            # Replace `{task}` with `{task[name]}` in templates
            value_queue = collections.deque()
            value_queue.append(templates_data)
            while value_queue:
                item = value_queue.popleft()
                if not isinstance(item, dict):
                    continue

                for key in tuple(item.keys()):
                    value = item[key]
                    if isinstance(value, dict):
                        value_queue.append(value)

                    elif isinstance(value, StringType):
                        item[key] = value.replace("{task}", "{task[name]}")
        return anatomy_data

    def reset(self):
        """Reset values of cached data in templates and roots objects."""
        self._data = self._prepare_anatomy_data(
            get_anatomy_settings(self.project_name, self._site_name)
        )
        self.templates_obj.reset()
        self.roots_obj.reset()

    @property
    def templates(self):
        """Wrap property `templates` of Anatomy's AnatomyTemplates instance."""
        return self._templates_obj.templates

    @property
    def templates_obj(self):
        """Return `AnatomyTemplates` object of current Anatomy instance."""
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
        """Return OPENPYPE_ROOT_* environments for current project in dict."""
        return self._roots_obj.root_environments()

    def root_environmets_fill_data(self, template=None):
        """Environment variable values in dictionary for rootless path.

        Args:
            template (str): Template for environment variable key fill.
                By default is set to `"${}"`.
        """
        return self.roots_obj.root_environmets_fill_data(template)

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
        """Set OPENPYPE_ROOT_* environments for current project."""
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
            root_templates.append("{" + group + "}")

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

    @classmethod
    def fill_root_with_path(cls, rootless_path, root_path):
        """Fill path without filled "root" key with passed path.

        This is helper to fill root with different directory path than anatomy
        has defined no matter if is single or multiroot.

        Output path is same as input path if `rootless_path` does not contain
        unfilled root key.

        Args:
            rootless_path (str): Path without filled "root" key. Example:
                "{root[work]}/MyProject/..."
            root_path (str): What should replace root key in `rootless_path`.

        Returns:
            str: Path with filled root.
        """
        output = str(rootless_path)
        for group in re.findall(cls.root_key_regex, rootless_path):
            replacement = "{" + group + "}"
            output = output.replace(replacement, root_path)

        return output

    def replace_root_with_env_key(self, filepath, template=None):
        """Replace root of path with environment key.

        # Example:
        ## Project with roots:
        ```
        {
            "nas": {
                "windows": P:/projects",
                ...
            }
            ...
        }
        ```

        ## Entered filepath
        "P:/projects/project/asset/task/animation_v001.ma"

        ## Entered template
        "<{}>"

        ## Output
        "<OPENPYPE_PROJECT_ROOT_NAS>/project/asset/task/animation_v001.ma"

        Args:
            filepath (str): Full file path where root should be replaced.
            template (str): Optional template for environment key. Must
                have one index format key.
                Default value if not entered: "${}"

        Returns:
            str: Path where root is replaced with environment root key.

        Raise:
            ValueError: When project's roots were not found in entered path.
        """
        success, rootless_path = self.find_root_template_from_path(filepath)
        if not success:
            raise ValueError(
                "{}: Project's roots were not found in path: {}".format(
                    self.project_name, filepath
                )
            )

        data = self.root_environmets_fill_data(template)
        return rootless_path.format(**data)


class AnatomyTemplateUnsolved(TemplateUnsolved):
    """Exception for unsolved template when strict is set to True."""

    msg = "Anatomy template \"{0}\" is unsolved.{1}{2}"


class AnatomyTemplateResult(TemplateResult):
    rootless = None

    def __new__(cls, result, rootless_path):
        new_obj = super(AnatomyTemplateResult, cls).__new__(
            cls,
            str(result),
            result.template,
            result.solved,
            result.used_values,
            result.missing_keys,
            result.invalid_types
        )
        new_obj.rootless = rootless_path
        return new_obj

    def validate(self):
        if not self.solved:
            raise AnatomyTemplateUnsolved(
                self.template,
                self.missing_keys,
                self.invalid_types
            )


class AnatomyTemplates(TemplatesDict):
    inner_key_pattern = re.compile(r"(\{@.*?[^{}0]*\})")
    inner_key_name_pattern = re.compile(r"\{@(.*?[^{}0]*)\}")

    def __init__(self, anatomy):
        super(AnatomyTemplates, self).__init__()
        self.anatomy = anatomy
        self.loaded_project = None

    def __getitem__(self, key):
        return self.templates[key]

    def get(self, key, default=None):
        return self.templates.get(key, default)

    def reset(self):
        self._raw_templates = None
        self._templates = None
        self._objected_templates = None

    @property
    def project_name(self):
        return self.anatomy.project_name

    @property
    def roots(self):
        return self.anatomy.roots

    @property
    def templates(self):
        self._validate_discovery()
        return self._templates

    @property
    def objected_templates(self):
        self._validate_discovery()
        return self._objected_templates

    def _validate_discovery(self):
        if self.project_name != self.loaded_project:
            self.reset()

        if self._templates is None:
            self._discover()
            self.loaded_project = self.project_name

    def _format_value(self, value, data):
        if isinstance(value, RootItem):
            return self._solve_dict(value, data)

        result = super(AnatomyTemplates, self)._format_value(value, data)
        if isinstance(result, TemplateResult):
            rootless_path = self._rootless_path(result, data)
            result = AnatomyTemplateResult(result, rootless_path)
        return result

    def set_templates(self, templates):
        if not templates:
            self.reset()
            return

        self._raw_templates = copy.deepcopy(templates)
        templates = copy.deepcopy(templates)
        v_queue = collections.deque()
        v_queue.append(templates)
        while v_queue:
            item = v_queue.popleft()
            if not isinstance(item, dict):
                continue

            for key in tuple(item.keys()):
                value = item[key]
                if isinstance(value, dict):
                    v_queue.append(value)

                elif (
                    isinstance(value, StringType)
                    and "{task}" in value
                ):
                    item[key] = value.replace("{task}", "{task[name]}")

        solved_templates = self.solve_template_inner_links(templates)
        self._templates = solved_templates
        self._objected_templates = self.create_ojected_templates(
            solved_templates
        )

    def default_templates(self):
        """Return default templates data with solved inner keys."""
        return self.solve_template_inner_links(
            self.anatomy["templates"]
        )

    def _discover(self):
        """ Loads anatomy templates from yaml.
        Default templates are loaded if project is not set or project does
        not have set it's own.
        TODO: create templates if not exist.

        Returns:
            TemplatesResultDict: Contain templates data for current project of
                default templates.
        """

        if self.project_name is None:
            # QUESTION create project specific if not found?
            raise AssertionError((
                "Project \"{0}\" does not have his own templates."
                " Trying to use default."
            ).format(self.project_name))

        self.set_templates(self.anatomy["templates"])

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
        overridden in group if already contain value for the key.

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
        default_key_values = templates.pop("defaults", {})
        for key, value in tuple(templates.items()):
            if isinstance(value, dict):
                continue
            default_key_values[key] = templates.pop(key)

        # Pop "others" key before before expected keys are processed
        other_templates = templates.pop("others") or {}

        keys_by_subkey = {}
        for sub_key, sub_value in templates.items():
            key_values = {}
            key_values.update(default_key_values)
            key_values.update(sub_value)
            keys_by_subkey[sub_key] = cls.prepare_inner_keys(key_values)

        for sub_key, sub_value in other_templates.items():
            if sub_key in keys_by_subkey:
                log.warning((
                    "Key \"{}\" is duplicated in others. Skipping."
                ).format(sub_key))
                continue

            key_values = {}
            key_values.update(default_key_values)
            key_values.update(sub_value)
            keys_by_subkey[sub_key] = cls.prepare_inner_keys(key_values)

        default_keys_by_subkeys = cls.prepare_inner_keys(default_key_values)

        for key, value in default_keys_by_subkeys.items():
            keys_by_subkey[key] = value

        return keys_by_subkey

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

    def _rootless_path(self, result, final_data):
        used_values = result.used_values
        missing_keys = result.missing_keys
        template = result.template
        invalid_types = result.invalid_types
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

        output = str(result)
        for used_root_keys in root_keys:
            if not used_root_keys:
                continue

            used_value = used_values
            root_key = None
            for key in used_root_keys:
                used_value = used_value[key]
                if root_key is None:
                    root_key = key
                else:
                    root_key += "[{}]".format(key)

            root_key = "{" + root_key + "}"
            output = output.replace(str(used_value), root_key)

        return output

    def format(self, data, strict=True):
        copy_data = copy.deepcopy(data)
        roots = self.roots
        if roots:
            copy_data["root"] = roots
        result = super(AnatomyTemplates, self).format(copy_data)
        result.strict = strict
        return result

    def format_all(self, in_data, only_keys=True):
        """ Solves templates based on entered data.

        Args:
            data (dict): Containing keys to be filled into template.

        Returns:
            TemplatesResultDict: Output `TemplateResult` have `strict`
                attribute set to False so accessing unfilled keys in templates
                won't raise any exceptions.
        """
        return self.format(in_data, strict=False)


class RootItem(FormatObject):
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
        self, root_raw_data, name=None, parent_keys=None, parent=None
    ):
        lowered_platform_keys = {}
        for key, value in root_raw_data.items():
            lowered_platform_keys[key.lower()] = value
        self.raw_data = lowered_platform_keys
        self.cleaned_data = self._clean_roots(lowered_platform_keys)
        self.name = name
        self.parent_keys = parent_keys or []
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
            # Skip empty paths
            if not root_path:
                continue

            if mod_path.startswith(root_path):
                result = True
                replacement = "{" + self.full_key() + "}"
                output = replacement + mod_path[len(root_path):]
                break

        return (result, output)


class Roots:
    """Object which should be used for formatting "root" key in templates.

    Args:
        anatomy Anatomy: Anatomy object created for a specific project.
    """

    env_prefix = "OPENPYPE_PROJECT_ROOT"
    roots_filename = "roots.json"

    def __init__(self, anatomy):
        self.anatomy = anatomy
        self.loaded_project = None
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

        Concatenates prefix "OPENPYPE_ROOT" with root keys to create unique
        keys.

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
                    "OPENPYPE_ROOT_WORK": "P:/projects/work",
                    "OPENPYPE_ROOT_PUBLISH": "P:/projects/publish"
                }

            Short example when multiroot is not used::
                {
                    "OPENPYPE_ROOT": "P:/projects"
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

    def _root_environments(self, keys=None, roots=None):
        if not keys:
            keys = []
        if roots is None:
            roots = self.roots

        if isinstance(roots, RootItem):
            key_items = [self.env_prefix]
            for _key in keys:
                key_items.append(_key.upper())

            key = "_".join(key_items)
            # Make sure key and value does not contain unicode
            #   - can happen in Python 2 hosts
            return {str(key): str(roots.value)}

        output = {}
        for _key, _value in roots.items():
            _keys = list(keys)
            _keys.append(_key)
            output.update(self._root_environments(_keys, _value))
        return output

    def root_environmets_fill_data(self, template=None):
        """Environment variable values in dictionary for rootless path.

        Args:
            template (str): Template for environment variable key fill.
                By default is set to `"${}"`.
        """
        if template is None:
            template = "${}"
        return self._root_environmets_fill_data(template)

    def _root_environmets_fill_data(self, template, keys=None, roots=None):
        if keys is None and roots is None:
            return {
                "root": self._root_environmets_fill_data(
                    template, [], self.roots
                )
            }

        if isinstance(roots, RootItem):
            key_items = [Roots.env_prefix]
            for _key in keys:
                key_items.append(_key.upper())
            key = "_".join(key_items)
            return template.format(key)

        output = {}
        for key, value in roots.items():
            _keys = list(keys)
            _keys.append(key)
            output[key] = self._root_environmets_fill_data(
                template, _keys, value
            )
        return output

    @property
    def project_name(self):
        """Return project name which will be used for loading root values."""
        return self.anatomy.project_name

    @property
    def roots(self):
        """Property for filling "root" key in templates.

        This property returns roots for current project or default root values.
        Warning:
            Default roots value may cause issues when project use different
            roots settings. That may happen when project use multiroot
            templates but default roots miss their keys.
        """
        if self.project_name != self.loaded_project:
            self._roots = None

        if self._roots is None:
            self._roots = self._discover()
            self.loaded_project = self.project_name
        return self._roots

    def _discover(self):
        """ Loads current project's roots or default.

        Default roots are loaded if project override's does not contain roots.

        Returns:
            `RootItem` or `dict` with multiple `RootItem`s when multiroot
            setting is used.
        """

        return self._parse_dict(self.anatomy["roots"], parent=self)

    @staticmethod
    def _parse_dict(data, key=None, parent_keys=None, parent=None):
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
        if not parent_keys:
            parent_keys = []
        is_last = False
        for value in data.values():
            if isinstance(value, StringType):
                is_last = True
                break

        if is_last:
            return RootItem(data, key, parent_keys, parent=parent)

        output = {}
        for _key, value in data.items():
            _parent_keys = list(parent_keys)
            _parent_keys.append(_key)
            output[_key] = Roots._parse_dict(value, _key, _parent_keys, parent)
        return output
