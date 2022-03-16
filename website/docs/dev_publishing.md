---
id: dev_publishing
title: Publishing
sidebar_label: Publishing
---

Publishing workflow consist of 2 parts:
- Creation - Mark what will be published and how.
- Publishing - Use data from creation to go through pyblish process.

OpenPype is using `pyblish` for publishing process. It is a little bit extented and modified mainly for UI purposes. The main differences are that OpenPype's publish UI allows to enable/disable instances or plugins during creation part instead of in publishing part and has limited actions only for failed validator plugins.

# Creation
Concept of creation does not have to "create" anything but prepare and store metadata about an "instance". Created instance always has `family` which defines what kind of data will be published, best example is `workfile` family. Storing of metadata is host specific and may be even a Creator plugin specific. In most of hosts are metadata stored to workfile (Maya scene, Nuke script, etc.) to an item or a node the same way so consistency of host implementation is kept, but some features may require different approach. Storing data to workfile gives ability to keep values so artist does not have to do create instances over and over.

## Created instance
Objected representation of created instance metadata defined by class **CreatedInstance**. Has access to **CreateContext** and **BaseCreator** that initialized the object. Is dictionary like object with few immutable keys (maked with start `*`) that are defined by creator plugin or create context on initialization. Can have more arbitrary data but keep in mind that some keys are reserved.

| Key | Type | Description |
|---|---|---|
| *id | str | Identifier of metadata type. ATM constant **"pyblish.avalon.instance"** |
| *instance_id | str | Unique ID of instance. Set automatically on instance creation using `str(uuid.uuid4())` |
| *family | str | Instance's family representing type defined by creator plugin. |
| *creator_identifier | str | Identifier of creator that collected/created the instance. |
| *creator_attributes | dict | Dictionary of attributes that are defined by creator plugin (`get_instance_attr_defs`). |
| *publish_attributes | dict | Dictionary of attributes that are defined by publish plugins. |
| variant | str | Variant is entered by artist on creation and may affect **subset**. |
| subset | str | Name of instance. This name will be used as subset name during publishing. |
| active | bool | Is instance active and will be published or not. |
| asset | str | Name of asset in which context was created. |
| task | str | Name of task in which context was created. Can be set to `None`. |

Task should not be required until subset name template expect it.

## Create plugin
Main responsibility of create plugin is to create, update, collect and remove instance metadata and propagate changes to create context. Has access to **CreateContext** (`self.create_context`) that discovered the plugin so has also access to other creators and instances.

### BaseCreator
Base implementation of creator plugin. It is not recommended to use this class as base for production plugins but rather use one of **AutoCreator** and **Creator** variants.

**Abstractions**
- **`family`** (class attr) - Tells what kind of instance will be created.
```python
class WorkfileCreator(Creator):
    family = "workfile"
```

- **`collect_instances`** (method) - Collect already existing instances from workfile and add them to create context. This method is called on initialization or reset of **CreateContext**. Each creator is responsible to find it's instances metadata, convert them to **CreatedInstance** object and add the to create context (`self._add_instance_to_context(instnace_obj)`).
```python
def collect_instances(self):
    # Using 'pipeline.list_instances' is just example how to get existing instances from scene
    # - getting existing instances is different per host implementation
    for instance_data in pipeline.list_instances():
        # Process only instances that were created by this creator
        creator_id = instance_data.get("creator_identifier")
        if creator_id == self.identifier:
            # Create instance object from existing data
            instance = CreatedInstance.from_existing(
                instance_data, self
            )
            # Add instance to create context
            self._add_instance_to_context(instance)
```

- **`create`** (method) - Create new object of **CreatedInstance** store it's metadata to workfile and add the instance into create context. Failed creation should raise **CreatorError** if happens error that can artist fix or give him some useful information. Trigger and implementation differs for **Creator** and **AutoCreator**.

- **`update_instances`** (method) - Update data of instances. Receives tuple with **instance** and **changes**.
```python
def update_instances(self, update_list):
    # Loop over changed instances
    for instance, changes in update_list:
        # Example possible usage of 'changes' to use different node on change
        #   of node id in instance data (MADE UP)
        node = None
        if "node_id" in changes:
            old_value, new_value = changes["node_id"]
            if new_value is not None:
                node = pipeline.get_node_by_id(new_value)

        if node is None:
            node = pipeline.get_node_by_instance_id(instance.id)
        # Get node in scene that represents the instance
        # Imprind data to a node
        pipeline.imprint(node, instance.data_to_store())


# Most implementations will probably ignore 'changes' completely
def update_instances(self, update_list):
    for instance, _ in update_list:
        # Get node from scene
        node = pipeline.get_node_by_instance_id(instance.id)
        # Imprint data to node
        pipeline.imprint(node, instance.data_to_store())
```

- **`remove_instances`** (method) - Remove instance metadata from workfile and from create context.
```python
# Possible way how to remove instance
def remove_instances(self, instances):
    for instance in instances:
        # Remove instance metadata from workflle
        pipeline.remove_instance(instance.id)
        # Remove instance from create context
        self._remove_instance_from_context(instance)


# Default implementation of `AutoCreator`
def remove_instances(self, instances):
    pass
```

:::note
When host implementation use universal way how to store and load instances you should implement host specific creator plugin base class with implemented **collect_instances**, **update_instances** and **remove_instances**.
:::

**Optional implementations**

- **`enabled`** (attr) - Boolean if creator plugin is enabled and used.
- **`identifier`** (class attr) - Consistent unique string identifier of the creator plugin. Is used to identify source plugin of existing instances. There can't be 2 creator plugins with same identifier. Default implementation returns `family` attribute.
```python
class RenderLayerCreator(Creator):
    family = "render"
    identifier = "render_layer"


class RenderPassCreator(Creator):
    family = "render"
    identifier = "render_pass"
```

- **`label`** (attr) - String label of creator plugin which will showed in UI, `identifier` is used when not set. It should be possible to use html tags.
```python
class RenderLayerCreator(Creator):
    label = "Render Layer"
```

- **`icon`** (attr) - Icon of creator and it's instances. Value can be a path to image file, full name of qtawesome icon, `QPixmap` or `QIcon`. For complex cases or cases when `Qt` objects are returned it is recommended to override `get_icon` method and handle the logic or import `Qt` inside the method to not break headless usage of creator plugin. For list of qtawesome icons check qtawesome github repository (look for used version in pyproject.toml).
- **`get_icon`** (method) - Default implementation returns `self.icon`.
```python
class RenderLayerCreator(Creator):
    # Use font awesome 5 icon
    icon = "fa5.building"
```


- **`get_instance_attr_defs`** (method) - Attribute definitions of instance. Creator can define attribute values with default values for each instance. These attributes may affect how will be instance processed during publishing. Attribute defiitions can be used from `openpype.pipeline.lib.attribute_definitions` (NOTE: Will be moved to `openpype.lib.attribute_definitions` soon). Attribute definitions define basic type of values for different cases e.g. boolean, number, string, enumerator, etc. Their advantage is that they can be created dynamically and
```python
from openpype.pipeline import attribute_definitions


class RenderLayerCreator(Creator):
    def get_instance_attr_defs(self):
        # Return empty list if '_allow_farm_render' is not enabled (can be set during initialization)
        if not self._allow_farm_render:
            return []
        # Give artist option to change if should be rendered on farm or locally
        return [
            attribute_definitions.BoolDef(
                "render_farm",
                default=False,
                label="Render on Farm"
            )
        ]
```

- **`get_subset_name`** (method) - Calculate subset name based on passed data. Data can be extended using `get_dynamic_data` method.  Default implementation is using `get_subset_name` from `openpype.lib` which is recommended.

- **`get_dynamic_data`** (method) - Can be used to extend data for subset template which may be required in some cases.


### AutoCreator
Creator that is triggered on reset of create context. Can be used for families that are expected to be created automatically without artist interaction (e.g. **workfile**). Method `create` is triggered after collecting of all creators.

:::important
**AutoCreator** has implemented **remove_instances** to do nothing as removing of auto created instances would in most of cases lead to create new instance immediately.
:::

```python
def __init__(
    self, create_context, system_settings, project_settings, *args, **kwargs
):
    super(MyCreator, self).__init__(
        create_context, system_settings, project_settings, *args, **kwargs
    )
    # Get variant value from settings
    variant_name = (
        project_settings["my_host"][self.identifier]["variant"]
    ).strip()
    if not variant_name:
        variant_name = "Main"
    self._variant_name = variant_name

# Create does not expect any arguments
def create(self):
    # Look for existing instance in create  context
    existing_instance = None
    for instance in self.create_context.instances:
        if instance.creator_identifier == self.identifier:
            existing_instance = instance
            break

    # Collect current context information
    # - variant can be filled from settings
    variant = self._variant_name
    # Only place where we can look for current context
    project_name = io.Session["AVALON_PROJECT"]
    asset_name = io.Session["AVALON_ASSET"]
    task_name = io.Session["AVALON_TASK"]
    host_name = io.Session["AVALON_APP"]

    # Create new instance if does not exist yet
    if existing_instance is None:
        asset_doc = io.find_one({"type": "asset", "name": asset_name})
        subset_name = self.get_subset_name(
            variant, task_name, asset_doc, project_name, host_name
        )
        data = {
            "asset": asset_name,
            "task": task_name,
            "variant": variant
        }
        data.update(self.get_dynamic_data(
            variant, task_name, asset_doc, project_name, host_name
        ))

        new_instance = CreatedInstance(
            self.family, subset_name, data, self
        )
        self._add_instance_to_context(new_instance)

    # Update instance context if is not the same
    elif (
        existing_instance["asset"] != asset_name
        or existing_instance["task"] != task_name
    ):
        asset_doc = io.find_one({"type": "asset", "name": asset_name})
        subset_name = self.get_subset_name(
            variant, task_name, asset_doc, project_name, host_name
        )
        existing_instance["asset"] = asset_name
        existing_instance["task"] = task_name
```

### Creator
Implementation of creator plugin that is triggered manually by artist in UI (or by code). Has extended options for UI purposes than **AutoCreator** and **create** method expect more arguments.

- **`create_allow_context_change`** (class attr) - Allow to set context in UI before creation. Some creator may not allow it or their logic would not use the context selection (e.g. bulk creators).
```python
class BulkRenderCreator(Creator):
    create_allow_context_change = False
```
- **`get_default_variants`** (method) - Returns list of default variants that are showed in create dialog. Uses **default_variants** by default.
- **`default_variants`** (attr) - Attribute for default implementation of **get_default_variants**.

- **`get_default_variant`** (method) - Return default variant that is prefilled in UI. By default returns `None`, in that case first item from **get_default_variants** is used if there is any or **"Main"**.

- **`get_description`** (method) - Returns short string description of creator. Uses **description** by default.
- **`description`** (attr) - Attribute for default implementation of **get_description**.

- **`get_detailed_description`** (method) - Returns detailed string description of creator. Can contain markdown. Uses **detailed_description** by default.
- **`detailed_description`** (attr) - Attribute for default implementation of **get_detailed_description**.

- **`get_pre_create_attr_defs`** (method) - Similar to **get_instance_attr_defs** returns attribute definitions but they are filled before creation. When creation is called from UI the values are passed to **create** method.

- **`create`** (method) - Code where creation of metadata

```python
from openpype.pipeline import attribute_definitions


class RenderLayerCreator(Creator):
    def __init__(
        self, context, system_settings, project_settings, *args, **kwargs
    ):
        super(RenderLayerCreator, self).__init__(
            context, system_settings, project_settings, *args, **kwargs
        )
        plugin_settings = (
            project_settings["my_host"]["create"][self.__class__.__name__]
        )
        self._allow_farm_render = plugin_settings["allow_farm_render"]

    def get_instance_attr_defs(self):
        # Return empty list if '_allow_farm_render' is not enabled (can be set during initialization)
        if not self._allow_farm_render:
            return []
        # Give artist option to change if should be rendered on farm or locally
        return [
            attribute_definitions.BoolDef(
                "render_farm",
                default=False,
                label="Render on Farm"
            )
        ]

    def get_pre_create_attr_defs(self):
        return [
            # Give user option to use selection or not
            attribute_definitions.BoolDef(
                "use_selection",
                default=False,
                label="Use selection"
            ),
            # Set to render on farm in creator dialog
            # - this value is not automatically passed to instance attributes
            #   creator must do that during creation
            attribute_definitions.BoolDef(
                "render_farm",
                default=False,
                label="Render on Farm"
            )
        ]

    def create(self, subset_name, instance_data, pre_create_data):
        # ARGS:
        # - 'subset_name' - precalculated subset name
        # - 'instance_data' - context data
        #    - 'asset' - asset name
        #    - 'task' - task name
        #    - 'variant' - variant
        #    - 'family' - instnace family
        # Check if should use selection or not
        if pre_create_data.get("use_selection"):
            items = pipeline.get_selection()
        else:
            items = [pipeline.create_write()]

        # Validations related to selection
        if len(items) > 1:
            raise CreatorError("Please select only single item at time.")

        elif not items:
            raise CreatorError("Nothing to create. Select at least one item.")

        # Create instence object
        new_instance = CreatedInstance(self.family, subset_name, data, self)
        # Pass value from pre create attribute to instance
        # - use them only when pre create date contain the data
        if "render_farm" in pre_create_data:
            use_farm = pre_create_data["render_farm"]
            new_instance.creator_attributes["render_farm"] = use_farm

        # Store metadata to workfile
        pipeline.imprint(new_instance.id, new_instance.data_to_store())

        # Add instance to context
        self._add_instance_to_context(new_instance)
```

## Create context
Controller and wrapper around creation is `CreateContext` which cares about loading  `CreatedInstance`

# Publish
OpenPype is using `pyblish` for publishing process which is a little bit extented and modified mainly for UI purposes. The main differences are that OpenPype's publish UI does not allow to enable/disable instances or plugins that can be done during creation part. Also does support actions only for validators after validation exception.

## Exceptions
OpenPype define few specific exceptions that should be used in publish plugins.

### Validation exception
Validation plugins should raise `PublishValidationError` to show to an artist what's wrong and give him actions to fix it. The exception says that error happened in plugin can be fixed by artist himself (with or without action on plugin). Any other errors will stop publishing immediately. Exception `PublishValidationError` raised after validation order has same effect as any other exception.

Exception `PublishValidationError` 3 arguments:
- **message** Which is not used in UI but for headless publishing.
- **title** Short description of error (2-5 words). Title is used for grouping of exceptions per plugin.
- **description** Detailed description of happened issue where markdown and html can be used.


### Known errors
When there is a known error that can't be fixed by user (e.g. can't connect to deadline service, etc.) `KnownPublishError` should be raise. The only difference is that it's message is shown in UI to artist otherwise a neutral message without context is shown.

## Plugin extension
Publish plugins can be extended by additional logic when inherits from `OpenPypePyblishPluginMixin` which can be used as mixin (additional inheritance of class).

```python
import pyblish.api
from openpype.pipeline import OpenPypePyblishPluginMixin


# Example context plugin
class MyExtendedPlugin(
    pyblish.api.ContextPlugin, OpenPypePyblishPluginMixin
):
    pass

```

### Extensions
Currently only extension is ability to define attributes for instances during creation. Method `get_attribute_defs` returns attribute definitions for families defined in plugin's `families` attribute if it's instance plugin or for whole context if it's context plugin. To convert existing values (or to remove legacy values) can be implemented `convert_attribute_values`. Values of publish attributes from created instance are never removed automatically so implementing of this method is best way to remove legacy data or convert them to new data structure.

Possible attribute definitions can be found in `openpype/pipeline/lib/attribute_definitions.py`.
