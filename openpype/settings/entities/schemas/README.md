# Creating GUI schemas

## Basic rules
- configurations does not define GUI, but GUI defines configurations!
- output is always json serializable
- GUI schema has multiple input types, all inputs are represented by a dictionary
- each input may have "input modifiers" (keys in dictionary) that are required or optional
    - only required modifier for all input items is key `"type"` which says what type of item it is
- there are special keys across all inputs
    - `"is_file"` - this key is for storing openpype defaults in `openpype` repo
        - reasons of existence: developing new schemas does not require to create defaults manually
        - key is validated, must be once in hierarchy else it won't be possible to store openpype defaults
    - `"is_group"` - define that all values under key in hierarchy will be overridden if any value is modified, this information is also stored to overrides
        - this keys is not allowed for all inputs as they may have not reason for that
        - key is validated, can be only once in hierarchy but is not required
- currently there are `system settings` and `project settings`
- all entities can have set `"tooltip"` key with description which will be shown in UI

## Inner schema
- GUI schemas are huge json files, to be able to split whole configuration into multiple schema there's type `schema`
- system configuration schemas are stored in `~/openpype/settings/entities/schemas/system_schema/` and project configurations in `~/openpype/settings/entities/schemas/projects_schema/`
- each schema name is filename of json file except extension (without ".json")
- if content is dictionary content will be used as `schema` else will be used as `schema_template`

### schema
- can have only key `"children"` which is list of strings, each string should represent another schema (order matters) string represents name of the schema
- will just paste schemas from other schema file in order of "children" list

```
{
    "type": "schema",
    "name": "my_schema_name"
}
```

### template
- allows to define schema "templates" to not duplicate same content multiple times
- legacy name is `schema_template` (still usable)
```javascript
// EXAMPLE json file content (filename: example_template.json)
[
    {
        "__default_values__": {
            "multipath_executables": true
        }
    }, {
        "type": "raw-json",
        "label": "{host_label} Environments",
        "key": "{host_name}_environments",
        "env_group_key": "{host_name}"
    }, {
        "type": "path",
        "key": "{host_name}_executables",
        "label": "{host_label} - Full paths to executables",
        "multiplatform": "{multipath_executables}",
        "multipath": true
    }
]
```
```javascript
// EXAMPLE usage of the template in schema
{
    "type": "dict",
    "key": "template_examples",
    "label": "Schema template examples",
    "children": [
        {
            "type": "template",
            // filename of template (example_template.json)
            "name": "example_template",
            "template_data": {
                "host_label": "Maya 2019",
                "host_name": "maya_2019",
                "multipath_executables": false
            }
        }, {
            "type": "template",
            "name": "example_template",
            "template_data": {
                "host_label": "Maya 2020",
                "host_name": "maya_2020"
            }
        }
    ]
}
```
- item in schema mush contain `"type"` and `"name"` keys but it is also expected that `"template_data"` will be entered too
- all items in the list, except `__default_values__`, will replace `schema_template` item in schema
- template may contain another template or schema
- it is expected that schema template will have unfilled fields as in example
    - unfilled fields are allowed only in values of schema dictionary
```javascript
{
    ...
    // Allowed
    "key": "{to_fill}"
    ...
    // Not allowed
    "{to_fill}": "value"
    ...
}
```
- Unfilled fields can be also used for non string values(e.g. dictionary), in that case value must contain only one key and value for fill must contain right type.
```javascript
// Passed data
{
    "executable_multiplatform": {
        "type": "schema",
        "name": "my_multiplatform_schema"
    }
}
// Template content
{
    ...
    // Allowed
    "multiplatform": "{executable_multiplatform}"
    ...
    // Not allowed
    "multiplatform": "{executable_multiplatform}_enhanced_string"
    ...
}
```
- It is possible to define default values for unfilled fields to do so one of items in list must be dictionary with key `"__default_values__"` and value as dictionary with default key: values (as in example above).

### dynamic_schema
- dynamic templates that can be defined by class of `ModuleSettingsDef`
- example:
```
{
    "type": "dynamic_schema",
    "name": "project_settings/global"
}
```
- all valid `BaseModuleSettingsDef` classes where calling of `get_settings_schemas`
    will return dictionary where is key "project_settings/global" with schemas
    will extend and replace this item
- dynamic schemas work almost the same way as templates
    - one item can be replaced by multiple items (or by 0 items)
- goal is to dynamically loaded settings of OpenPype addons without having
    their schemas or default values in main repository
    - values of these schemas are saved using the `BaseModuleSettingsDef` methods
- easiest is to use `JsonFilesSettingsDef` which has full implementation of storing default values to json files all you have to implement is method `get_settings_root_path` which should return path to root directory where settings schema can be found and will be saved

## Basic Dictionary inputs
- these inputs wraps another inputs into {key: value} relation

## dict
- this is dictionary type wrapping more inputs with keys defined in schema
- may be used as dynamic children (e.g. in `list` or `dict-modifiable`)
    - in that case the only key modifier is `children` which is list of it's keys
    - USAGE: e.g. List of dictionaries where each dictionary have same structure.
- if is not used as dynamic children then must have defined `"key"` under which are it's values stored
- may be with or without `"label"` (only for GUI)
    - `"label"` must be set to be able mark item as group with `"is_group"` key set to True
- item with label can visually wrap it's children
    - this option is enabled by default to turn off set `"use_label_wrap"` to `False`
    - label wrap is by default collapsible
        - that can be set with key `"collapsible"` to `True`/`False`
        - with key `"collapsed"` as `True`/`False` can be set that is collapsed when GUI is opened (Default: `False`)
    - it is possible to add lighter background with `"highlight_content"` (Default: `False`)
        - lighter background has limits of maximum applies after 3-4 nested highlighted items there is not much difference in the color
    - output is dictionary `{the "key": children values}`
```
# Example
{
    "key": "applications",
    "type": "dict",
    "label": "Applications",
    "collapsible": true,
    "highlight_content": true,
    "is_group": true,
    "is_file": true,
    "children": [
        ...ITEMS...
    ]
}

# Without label
{
    "type": "dict",
    "key": "global",
    "children": [
        ...ITEMS...
    ]
}

# When used as widget
{
    "type": "list",
    "key": "profiles",
    "label": "Profiles",
    "object_type": {
        "type": "dict",
        "children": [
            {
                "key": "families",
                "label": "Families",
                "type": "list",
                "object_type": "text"
            }, {
                "key": "hosts",
                "label": "Hosts",
                "type": "list",
                "object_type": "text"
            }
            ...
        ]
    }
}
```

## dict-roots
- entity can be used only in Project settings
- keys of dictionary are based on current project roots
- they are not updated "live" it is required to save root changes and then
    modify values on this entity
    # TODO do live updates
```
{
    "type": "dict-roots",
    "key": "roots",
    "label": "Roots",
    "object_type": {
        "type": "path",
        "multiplatform": true,
        "multipath": false
    }
}
```

## dict-conditional
- is similar to `dict` but has always available one enum entity
    - the enum entity has single selection and it's value define other children entities
- each value of enumerator have defined children that will be used
    - there is no way how to have shared entities across multiple enum items
- value from enumerator is also stored next to other values
    - to define the key under which will be enum value stored use `enum_key`
    - `enum_key` must match key regex and any enum item can't have children with same key
    - `enum_label` is label of the entity for UI purposes
- enum items are define with `enum_children`
    - it's a list where each item represents single item for the enum
    - all items in `enum_children` must have at least `key` key which represents value stored under `enum_key`
    - enum items can define `label` for UI purposes
    - most important part is that item can define `children` key where are definitions of it's children (`children` value works the same way as in `dict`)
- to set default value for `enum_key` set it with `enum_default`
- entity must have defined `"label"` if is not used as widget
- is set as group if any parent is not group (can't have children as group)
- may be with or without `"label"` (only for GUI)
    - `"label"` must be set to be able mark item as group with `"is_group"` key set to True
- item with label can visually wrap it's children
    - this option is enabled by default to turn off set `"use_label_wrap"` to `False`
    - label wrap is by default collapsible
        - that can be set with key `"collapsible"` to `True`/`False`
        - with key `"collapsed"` as `True`/`False` can be set that is collapsed when GUI is opened (Default: `False`)
    - it is possible to add lighter background with `"highlight_content"` (Default: `False`)
        - lighter background has limits of maximum applies after 3-4 nested highlighted items there is not much difference in the color
- for UI porposes was added `enum_is_horizontal` which will make combobox appear next to children inputs instead of on top of them (Default: `False`)
    - this has extended ability of `enum_on_right` which will move combobox to right side next to children widgets (Default: `False`)
- output is dictionary `{the "key": children values}`
- using this type as template item for list type can be used to create infinite hierarchies

```
# Example
{
    "type": "dict-conditional",
    "key": "my_key",
    "label": "My Key",
    "enum_key": "type",
    "enum_label": "label",
    "enum_children": [
        # Each item must be a dictionary with 'key'
        {
            "key": "action",
            "label": "Action",
            "children": [
                {
                    "type": "text",
                    "key": "key",
                    "label": "Key"
                },
                {
                    "type": "text",
                    "key": "label",
                    "label": "Label"
                },
                {
                    "type": "text",
                    "key": "command",
                    "label": "Comand"
                }
            ]
        },
        {
            "key": "menu",
            "label": "Menu",
            "children": [
                {
                    "key": "children",
                    "label": "Children",
                    "type": "list",
                    "object_type": "text"
                }
            ]
        },
        {
            # Separator does not have children as "separator" value is enough
            "key": "separator",
            "label": "Separator"
        }
    ]
}
```

How output of the schema could look like on save:
```
{
    "type": "separator"
}

{
    "type": "action",
    "key": "action_1",
    "label": "Action 1",
    "command": "run command -arg"
}

{
    "type": "menu",
    "children": [
        "child_1",
        "child_2"
    ]
}
```

## Inputs for setting any kind of value (`Pure` inputs)
- all inputs must have defined `"key"` if are not used as dynamic item
    - they can also have defined `"label"`

### boolean
- simple checkbox, nothing more to set
```
{
    "type": "boolean",
    "key": "my_boolean_key",
    "label": "Do you want to use Pype?"
}
```

### number
- number input, can be used for both integer and float
    - key `"decimal"` defines how many decimal places will be used, 0 is for integer input (Default: `0`)
    - key `"minimum"` as minimum allowed number to enter (Default: `-99999`)
    - key `"maxium"` as maximum allowed number to enter (Default: `99999`)
- key `"steps"` will change single step value of UI inputs (using arrows and wheel scroll)
- for UI it is possible to show slider to enable this option set `show_slider` to `true`
```
{
    "type": "number",
    "key": "fps",
    "label": "Frame rate (FPS)"
    "decimal": 2,
    "minimum": 1,
    "maximum": 300000
}
```

```
{
    "type": "number",
    "key": "ratio",
    "label": "Ratio"
    "decimal": 3,
    "minimum": 0,
    "maximum": 1,
    "show_slider": true
}
```

### text
- simple text input
    - key `"multiline"` allows to enter multiple lines of text (Default: `False`)
    - key `"placeholder"` allows to show text inside input when is empty (Default: `None`)

```
{
    "type": "text",
    "key": "deadline_pool",
    "label": "Deadline pool"
}
```

### path-input
- this input is implemented to add additional features to text input
- this is meant to be used in proxy input `path`
    - DO NOT USE this input in schema please

### raw-json
- a little bit enhanced text input for raw json
- can store dictionary (`{}`) or list (`[]`) but not both
    - by default stores dictionary to change it to list set `is_list` to `True`
- has validations of json format
- output can be stored as string
    - this is to allow any keys in dictionary
    - set key `store_as_string` to `true`
    - code using that setting must expected that value is string and use json module to convert it to python types

```
{
    "type": "raw-json",
    "key": "profiles",
    "label": "Extract Review profiles",
    "is_list": true
}
```

### enum
- enumeration of values that are predefined in schema
- multiselection can be allowed with setting key `"multiselection"` to `True` (Default: `False`)
- values are defined under value of key `"enum_items"` as list
    - each item in list is simple dictionary where value is label and key is value which will be stored
    - should be possible to enter single dictionary if order of items doesn't matter
- it is possible to set default selected value/s with `default` attribute
    - it is recommended to use this option only in single selection mode
    - at the end this option is used only when defying default settings value or in dynamic items

```
{
    "key": "tags",
    "label": "Tags",
    "type": "enum",
    "multiselection": true,
    "enum_items": [
        {"burnin": "Add burnins"},
        {"ftrackreview": "Add to Ftrack"},
        {"delete": "Delete output"},
        {"slate-frame": "Add slate frame"},
        {"no-handles": "Skip handle frames"}
    ]
}
```

### anatomy-templates-enum
- enumeration of all available anatomy template keys
- have only single selection mode
- it is possible to define default value `default`
    - `"work"` is used if default value is not specified
- enum values are not updated on the fly it is required to save templates and
    reset settings to recache values
```
{
    "key": "host",
    "label": "Host name",
    "type": "anatomy-templates-enum",
    "default": "publish"
}
```

### hosts-enum
- enumeration of available hosts
- multiselection can be allowed with setting key `"multiselection"` to `True` (Default: `False`)
- it is possible to add empty value (represented with empty string) with setting `"use_empty_value"` to `True` (Default: `False`)
- it is possible to set `"custom_labels"` for host names where key `""` is empty value (Default: `{}`)
- to filter host names it is required to define `"hosts_filter"` which is list of host names that will be available
    - do not pass empty string if `use_empty_value` is enabled
    - ignoring host names would be more dangerous in some cases
```
{
    "key": "host",
    "label": "Host name",
    "type": "hosts-enum",
    "multiselection": false,
    "use_empty_value": true,
    "custom_labels": {
        "": "N/A",
        "nuke": "Nuke"
    },
    "hosts_filter": [
        "nuke"
    ]
}
```

### apps-enum
- enumeration of available application and their variants from system settings
    - applications without host name are excluded
- can be used only in project settings
- has only `multiselection`
- used only in project anatomy
```
{
    "type": "apps-enum",
    "key": "applications",
    "label": "Applications"
}
```

### tools-enum
- enumeration of available tools and their variants from system settings
- can be used only in project settings
- has only `multiselection`
- used only in project anatomy
```
{
    "type": "tools-enum",
    "key": "tools_env",
    "label": "Tools"
}
```

### task-types-enum
- enumeration of task types from current project
- enum values are not updated on the fly and modifications of task types on project require save and reset to be propagated to this enum
- has set `multiselection` to `True` but can be changed to `False` in schema

### deadline_url-enum
- deadline module specific enumerator using deadline system settings to fill it's values
- TODO: move this type to deadline module

## Inputs for setting value using Pure inputs
- these inputs also have required `"key"`
- attribute `"label"` is required in few conditions
    - when item is marked `as_group` or when `use_label_wrap`
- they use Pure inputs "as widgets"

### list
- output is list
- items can be added and removed
- items in list must be the same type
- to wrap item in collapsible widget with label on top set `use_label_wrap` to `True`
    - when this is used `collapsible` and `collapsed` can be set (same as `dict` item does)
- type of items is defined with key `"object_type"`
- there are 2 possible ways how to set the type:
    1.) dictionary with item modifiers (`number` input has `minimum`, `maximum` and `decimals`) in that case item type must be set as value of `"type"` (example below)
    2.) item type name as string without modifiers (e.g. `text`)
    3.) enhancement of 1.) there is also support of `template` type but be carefull about endless loop of templates
        - goal of using `template` is to easily change same item definitions in multiple lists

1.) with item modifiers
```
{
    "type": "list",
    "key": "exclude_ports",
    "label": "Exclude ports",
    "object_type": {
        "type": "number", # number item type
        "minimum": 1, # minimum modifier
        "maximum": 65535 # maximum modifier
    }
}
```

2.) without modifiers
```
{
    "type": "list",
    "key": "exclude_ports",
    "label": "Exclude ports",
    "object_type": "text"
}
```

3.) with template definition
```
# Schema of list item where template is used
{
    "type": "list",
    "key": "menu_items",
    "label": "Menu Items",
    "object_type": {
        "type": "template",
        "name": "template_object_example"
    }
}

# WARNING:
#  In this example the template use itself inside which will work in `list`
#  but may cause an issue in other entity types (e.g. `dict`).

'template_object_example.json' :
[
    {
        "type": "dict-conditional",
        "use_label_wrap": true,
        "collapsible": true,
        "key": "menu_items",
        "label": "Menu items",
        "enum_key": "type",
        "enum_label": "Type",
        "enum_children": [
            {
                "key": "action",
                "label": "Action",
                "children": [
                    {
                        "type": "text",
                        "key": "key",
                        "label": "Key"
                    }
                ]
            },
            {
                "key": "menu",
                "label": "Menu",
                "children": [
                    {
                        "key": "children",
                        "label": "Children",
                        "type": "list",
                        "object_type": {
                            "type": "template",
                            "name": "template_object_example"
                        }
                    }
                ]
            }
        ]
    }
]
```

### dict-modifiable
- one of dictionary inputs, this is only used as value input
- items in this input can be removed and added same way as in `list` input
- value items in dictionary must be the same type
- type of items is defined with key `"object_type"`
- required keys may be defined under `"required_keys"`
    - required keys must be defined as a list (e.g. `["key_1"]`) and are moved to the top
    - these keys can't be removed or edited (it is possible to edit label if item is collapsible)
- there are 2 possible ways how to set the type:
    1.) dictionary with item modifiers (`number` input has `minimum`, `maximum` and `decimals`) in that case item type must be set as value of `"type"` (example below)
    2.) item type name as string without modifiers (e.g. `text`)
- this input can be collapsible
    - that can be set with key `"collapsible"` as `True`/`False` (Default: `True`)
        - with key `"collapsed"` as `True`/`False` can be set that is collapsed when GUI is opened (Default: `False`)

1.) with item modifiers
```
{
    "type": "dict-modifiable",
    "object_type": {
        "type": "number",
        "minimum": 0,
        "maximum": 300
    },
    "is_group": true,
    "key": "templates_mapping",
    "label": "Muster - Templates mapping",
    "is_file": true
}
```

2.) without modifiers
```
{
    "type": "dict-modifiable",
    "object_type": "text",
    "is_group": true,
    "key": "templates_mapping",
    "label": "Muster - Templates mapping",
    "is_file": true
}
```

### path
- input for paths, use `path-input` internally
- has 2 input modifiers `"multiplatform"` and `"multipath"`
    - `"multiplatform"` - adds `"windows"`, `"linux"` and `"darwin"` path inputs result is dictionary
    - `"multipath"` - it is possible to enter multiple paths
    - if both are enabled result is dictionary with lists

```
{
    "type": "path",
    "key": "ffmpeg_path",
    "label": "FFmpeg path",
    "multiplatform": true,
    "multipath": true
}
```

### list-strict
- input for strict number of items in list
- each child item can be different type with different possible modifiers
- it is possible to display them in horizontal or vertical layout
    - key `"horizontal"` as `True`/`False` (Default: `True`)
- each child may have defined `"label"` which is shown next to input
    - label does not reflect modifications or overrides (TODO)
- children item are defined under key `"object_types"` which is list of dictionaries
    - key `"children"` is not used because is used for hierarchy validations in schema
- USAGE: For colors, transformations, etc. Custom number and different modifiers
  give ability to define if color is HUE or RGB, 0-255, 0-1, 0-100 etc.

```
{
    "type": "list-strict",
    "key": "color",
    "label": "Color",
    "object_types": [
        {
            "label": "Red",
            "type": "number",
            "minimum": 0,
            "maximum": 255,
            "decimal": 0
        }, {
            "label": "Green",
            "type": "number",
            "minimum": 0,
            "maximum": 255,
            "decimal": 0
        }, {
            "label": "Blue",
            "type": "number",
            "minimum": 0,
            "maximum": 255,
            "decimal": 0
        }, {
            "label": "Alpha",
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "decimal": 6
        }
    ]
}
```

### color
- preimplemented entity to store and load color values
- entity store and expect list of 4 integers in range 0-255
    - integers represents rgba [Red, Green, Blue, Alpha]

```
{
    "type": "color",
    "key": "bg_color",
    "label": "Background Color"
}
```

## Noninteractive widgets
- have nothing to do with data

### label
- add label with note or explanations
- it is possible to use html tags inside the label

```
{
    "type": "label",
    "label": "<span style=\"color:#FF0000\";>RED LABEL:</span> Normal label"
}
```

### separator
- legacy name is `splitter` (still usable)
- visual separator of items (more divider than separator)

```
{
    "type": "separator"
}
```

## Anatomy
Anatomy represents data stored on project document.

### anatomy
- entity works similarly to `dict`
- anatomy has always all keys overridden with overrides
    - overrides are not applied as all anatomy data must be available from project document
    - all children must be groups

## Proxy wrappers
- should wraps multiple inputs only visually
- these does not have `"key"` key and do not allow to have `"is_file"` or `"is_group"` modifiers enabled
- can't be used as widget (first item in e.g. `list`, `dict-modifiable`, etc.)

### form
- wraps inputs into form look layout
- should be used only for Pure inputs

```
{
    "type": "dict-form",
    "children": [
        {
            "type": "text",
            "key": "deadline_department",
            "label": "Deadline apartment"
        }, {
            "type": "number",
            "key": "deadline_priority",
            "label": "Deadline priority"
        }, {
           ...
        }
    ]
}
```


### collapsible-wrap
- wraps inputs into collapsible widget
    - looks like `dict` but does not hold `"key"`
- should be used only for Pure inputs

```
{
    "type": "collapsible-wrap",
    "label": "Collapsible example"
    "children": [
        {
            "type": "text",
            "key": "_example_input_collapsible",
            "label": "Example input in collapsible wrapper"
        }, {
           ...
        }
    ]
}
