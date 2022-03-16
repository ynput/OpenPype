# Create
Creation is process defying what and how will be published. May work in a different way based on host implementation.

## CreateContext
Entry point of creation. All data and metadata are handled through create context. Context hold all global data and instances. Is responsible for loading of plugins (create, publish), triggering creator methods, validation of host implementation and emitting changes to creators and host.

Discovers Creator plugins to be able create new instances and convert existing instances. Creators may have defined attributes that are specific for their instances. Attributes definition can enhance behavior of instance during publishing.

Publish plugins are loaded because they can also define attributes definitions. These are less family specific To be able define attributes Publish plugin must inherit from `OpenPypePyblishPluginMixin` and must override `get_attribute_defs` class method which must return list of attribute definitions. Values of publish plugin definitions are stored per plugin name under `publish_attributes`. Also can override `convert_attribute_values` class method which gives ability to modify values on instance before are used in CreatedInstance. Method `convert_attribute_values` can be also used without `get_attribute_defs` to modify values when changing compatibility (remove metadata from instance because are irrelevant).

Possible attribute definitions can be found in `openpype/pipeline/lib/attribute_definitions.py`.

Except creating and removing instances are all changes not automatically propagated to host context (scene/workfile/...) to propagate changes call `save_changes` which trigger update of all instances in context using Creators implementation.


## CreatedInstance
Product of creation is "instance" which holds basic data defying it. Core data are `creator_identifier`, `family` and `subset`. Other data can be keys used to fill subset name or metadata modifying publishing process of the instance (more described later). All instances have `id` which holds constant `pyblish.avalon.instance` and `instance_id` which is identifier of the instance.
Family tells how should be instance processed and subset what name will published item have.
- There are cases when subset is not fully filled during creation and may change during publishing. That is in most of cases caused because instance is related to other instance or instance data do not represent final product.

`CreatedInstance` is entity holding the data which are stored and used.

```python
{
    # Immutable data after creation
    ## Identifier that this data represents instance for publishing (automatically assigned)
    "id": "pyblish.avalon.instance",
    ## Identifier of this specific instance (automatically assigned)
    "instance_id": <uuid4>,
    ## Instance family (used from Creator)
    "family": <family>,

    # Mutable data
    ## Subset name based on subset name template - may change overtime (on context change)
    "subset": <subset>,
    ## Instance is active and will be published
    "active": True,
    ## Version of instance
    "version": 1,
    # Identifier of creator (is unique)
    "creator_identifier": "",
    ## Creator specific attributes (defined by Creator)
    "creator_attributes": {...},
    ## Publish plugin specific plugins (defined by Publish plugin)
    "publish_attributes": {
        # Attribute values are stored by publish plugin name
        #   - Duplicated plugin names can cause clashes!
        <Plugin name>: {...},
        ...
    },
    ## Additional data related to instance (`asset`, `task`, etc.)
    ...
}
```

## Creator
To be able create, update, remove or collect existing instances there must be defined a creator. Creator must have unique identifier and can represents a family. There can be multiple Creators for single family. Identifier of creator should contain family (advise).

Creator has abstract methods to handle instances. For new instance creation is used `create` which should create metadata in host context and add new instance object to `CreateContext`. To collect existing instances is used `collect_instances` which should find all existing instances related to creator and add them to `CreateContext`. To update data of instance is used `update_instances` which is called from `CreateContext` on `save_changes`. To remove instance use `remove_instances` which should remove metadata from host context and remove instance from `CreateContext`.

Creator has access to `CreateContext` which created object of the creator. All new instances or removed instances must be told to context. To do so use methods `_add_instance_to_context` and `_remove_instance_from_context` where `CreatedInstance` is passed. They should be called from `create` if new instance was created and from `remove_instances` if instance was removed.

Creators don't have strictly defined how are instances handled but it is good practice to define a way which is host specific. It is not strict because there are cases when host implementation just can't handle all requirements of all creators.

### AutoCreator
Auto-creators are automatically executed when `CreateContext` is reset. They can be used to create instances that should be always available and may not require artist's manual creation (e.g. `workfile`). Should not create duplicated instance and validate existence before creates a new. Method `remove_instances` is implemented to do nothing.

## Host
Host implementation must have available global context metadata handler functions. One to get current context data and second to update them. Currently are to context data stored only context publish plugin attribute values.

### Get global context data (`get_context_data`)
There are data that are not specific for any instance but are specific for whole context (e.g. Context plugins values).

### Update global context data (`update_context_data`)
Update global context data.

### Optional title of context
It is recommended to implement `get_context_title` function. String returned from this function will be shown in UI as context in which artist is.
