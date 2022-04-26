Subset manager
--------------

Simple UI showing list of created subset that will be published via Pyblish.
Useful for applications (Photoshop, AfterEffects, TVPaint, Harmony) which are
storing metadata about instance hidden from user.

This UI allows listing all created subset and removal of them if needed (
in case use doesn't want to publish anymore, its using workfile as a starting 
file for different task and instances should be completely different etc.
)

Host is expected to implemented:
- `list_instances` - returning list of dictionaries (instances), must contain
    unique uuid field
    example: 
    ```[{"uuid":"15","active":true,"subset":"imageBG","family":"image","id":"pyblish.avalon.instance","asset":"Town"}]```
- `remove_instance(instance)` - removes instance from file's metadata
    instance is a dictionary, with uuid field 