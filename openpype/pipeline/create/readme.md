# Create
Creation is process defying what and how will be published. May work in a different way based on host implementation.

## CreateContext
Entry point of creation. All data and metadata are stored to create context. Context hold all global data and instances. Is responsible for loading of plugins (create, publish), loading data from host, validation of host implementation and emitting changes to host implementation.

Discovers Create plugins to be able create new instances and convert existing instances. Creators may have defined attributes that are specific for the family. Attributes definition can enhance behavior of instance during publishing.

Publish plugins are loaded because they can also define attributes definitions. These are less family specific To be able define attributes Publish plugin must inherit from `OpenPypePyblishPluginMixin` and must override `get_attribute_defs` class method which must return list of attribute definitions. Values of publish plugin definitions are stored per plugin name under `publish_attributes`.

Possible attribute definitions can be found in `openpype/pipeline/lib/attribute_definitions.py`.


## CreatedInstance
Product of creation is "instance" which holds basic data defying it. Core data are `family` and `subset`. Other data can be keys used to fill subset name or metadata modifying publishing process of the instance (more described later).
Family tells how should be instance processed and subset what name will published item have.
- There are cases when subset is not fully filled during creation and may change during publishing. That is in most of cases caused because instance is related to other instance or instance data do not represent final product.

`CreatedInstance` is entity holding the data which are stored and used.

```python
{
    # Immutable data after creation
    ## Identifier that this data represents instance for publishing (automatically assigned)
    "id": "pyblish.avalon.instance",
    ## Identifier of this specific instance (automatically assigned)
    "uuid": <uuid4>,
    ## Instance family (used from Creator)
    "family": <family>,

    # Mutable data
    ## Subset name based on subset name template - may change overtime (on context change)
    "subset": <subset>,
    ## Instance is active and will be published
    "active": True,
    ## Version of instance
    "version": 1,
    ## Creator specific attributes (defined by Creator)
    "family_attributes": {...},
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
To be able create instance there must be defined a creator. Creator represents a family and handling of it's instances. Is not responsible only about creating new instances but also about updating existing. Family is identifier of creator so there can be only one Creator with same family at a time which helps to handle changes in creation of specific family.

Creator does not have strictly defined how is new instance created but result be approachable from host implementation and host must have ability to remove the instance metadata without the Creator. That is host specific logic and can't be handled generally.

### AutoCreator
Auto-creators are automatically executed when CreateContext is reset. They can be used to create instances that should be always available and may not require artist's manual creation (e.g. `workfile`). Should not create duplicated instance and should raise `AutoCreationSkipped` exception when did not create any instance to speed up resetting of context.

## Host
Host implementation should be main entrance for creators how their logic should work. In most of cases must store data somewhere ideally to workfile if host has workfile and it's possible.

Host implementation must have available these functions to be able handle creation changes.

### List all created instances (`list_instances`)
List of all instances for current context (from workfile). Each item is dictionary with all data that are stored. Creators must implement their creation so host will be able to find the instance with this function.

### Remove instances (`remove_instances`)
Remove instance from context (from workfile). This must remove all metadata about instance so instance is not retrieved with `list_instances`. This is default host implementation of instance removement. Creator can do more cleanup before this function is called and can stop calling of this function completely (e.g. when Creator removed node where are also stored metadata).

### Update instances (`update_instances`)
Instance data has changed and update of changes should be saved so next call of `list_instances` will return modified values.

### Get global context data (`get_context_data`)
There are data that are not specific for any instance but are specific for whole context (e.g. Context plugins values).

### Update global context data (`update_context_data`)
Update global context data.

### Get context title (`get_context_title`)
This is optional but is recommended. String returned from this function will be shown in UI.
