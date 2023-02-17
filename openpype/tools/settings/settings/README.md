# Creating GUI schemas

## Basic rules
- configurations does not define GUI, but GUI defines configurations!
- output is always json (yaml is not needed for anatomy templates anymore)
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
- currently there are `system configurations` and `project configurations`

## Inner schema
- GUI schemas are huge json files, to be able to split whole configuration into multiple schema there's type `schema`
- system configuration schemas are stored in `~/tools/settings/settings/gui_schemas/system_schema/` and project configurations in `~/tools/settings/settings/gui_schemas/projects_schema/`
- each schema name is filename of json file except extension (without ".json")
- if content is dictionary content will be used as `schema` else will be used as `schema_template`

### schema
- can have only key `"children"` which is list of strings, each string should represent another schema (order matters) string represebts name of the schema
- will just paste schemas from other schema file in order of "children" list

```
{
    "type": "schema",
    "name": "my_schema_name"
}
```

### schema_template
- allows to define schema "templates" to not duplicate same content multiple times
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
        "key": "{host_name}_environments"
    }, {
        "type": "path-widget",
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
    "key": "schema_template_examples",
    "label": "Schema template examples",
    "children": [
        {
            "type": "schema_template",
            // filename of template (example_template.json)
            "name": "example_template",
            "template_data": {
                "host_label": "Maya 2019",
                "host_name": "maya_2019",
                "multipath_executables": false
            }
        }, {
            "type": "schema_template",
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
- Unfilled fields can be also used for non string values, in that case value must contain only one key and value for fill must contain right type.
```javascript
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


## Basic Dictionary inputs
- these inputs wraps another inputs into {key: value} relation

## dict
- this is another dictionary input wrapping more inputs but visually makes them different
- item may be used as widget (in `list` or `dict-modifiable`)
    - in that case the only key modifier is `children` which is list of it's keys
    - USAGE: e.g. List of dictionaries where each dictionary have same structure.
- item may be with or without `"label"` if is not used as widget
    - required keys are `"key"` under which will be stored
    - without label it is just wrap item holding `"key"`
        - can't have `"is_group"` key set to True as it breaks visual override showing
    - if `"label"` is entetered there which will be shown in GUI
        - item with label can be collapsible
            - that can be set with key `"collapsible"` as `True`/`False` (Default: `True`)
                - with key `"collapsed"` as `True`/`False` can be set that is collapsed when GUI is opened (Default: `False`)
        - it is possible to add darker background with `"highlight_content"` (Default: `False`)
            - darker background has limits of maximum applies after 3-4 nested highlighted items there is not difference in the color
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

## Inputs for setting any kind of value (`Pure` inputs)
- all these input must have defined `"key"` under which will be stored and `"label"` which will be shown next to input
    - unless they are used in different types of inputs (later) "as widgets" in that case `"key"` and `"label"` are not required as there is not place where to set them

### boolean
- simple checkbox, nothing more to set
```
{
    "type": "boolean",
    "key": "my_boolean_key",
    "label": "Do you want to use OpenPype?"
}
```

### number
- number input, can be used for both integer and float
    - key `"decimal"` defines how many decimal places will be used, 0 is for integer input (Default: `0`)
    - key `"minimum"` as minimum allowed number to enter (Default: `-99999`)
    - key `"maximum"` as maximum allowed number to enter (Default: `99999`)
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
- enhanced text input
    - does not allow to enter backslash, is auto-converted to forward slash
    - may be added another validations, like do not allow end path with slash
- this input is implemented to add additional features to text input
- this is meant to be used in proxy input `path-widget`
    - DO NOT USE this input in schema please

### raw-json
- a little bit enhanced text input for raw json
- has validations of json format
    - empty value is invalid value, always must be at least `{}` of `[]`

```
{
    "type": "raw-json",
    "key": "profiles",
    "label": "Extract Review profiles"
}
```

### enum
- returns value of single on multiple items from predefined values
- multiselection can be allowed with setting key `"multiselection"` to `True` (Default: `False`)
- values are defined under value of key `"enum_items"` as list
    - each item in list is simple dictionary where value is label and key is value which will be stored
    - should be possible to enter single dictionary if order of items doesn't matter

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
        {"no-hnadles": "Skip handle frames"}
    ]
}
```

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

### path-widget
- input for paths, use `path-input` internally
- has 2 input modifiers `"multiplatform"` and `"multipath"`
    - `"multiplatform"` - adds `"windows"`, `"linux"` and `"darwin"` path inputs result is dictionary
    - `"multipath"` - it is possible to enter multiple paths
    - if both are enabled result is dictionary with lists

```
{
    "type": "path-widget",
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

### splitter
- visual splitter of items (more divider than splitter)

```
{
    "type": "splitter"
}
```

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
