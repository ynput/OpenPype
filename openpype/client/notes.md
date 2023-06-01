# Client functionality
## Reason
Preparation for OpenPype v4 server. Goal is to remove direct mongo calls in code to prepare a little bit for different source of data for code before. To start think about database calls less as mongo calls but more universally. To do so was implemented simple wrapper around database calls to not use pymongo specific code.

Current goal is not to make universal database model which can be easily replaced with any different source of data but to make it close as possible. Current implementation of OpenPype is too tightly connected to pymongo and it's abilities so we're trying to get closer with long term changes that can be used even in current state.

## Queries
Query functions don't use full potential of mongo queries like very specific queries based on subdictionaries or unknown structures. We try to avoid these calls as much as possible because they'll probably won't be available in future. If it's really necessary a new function can be added but only if it's reasonable for overall logic. All query functions were moved to `~/client/entities.py`. Each function has arguments with available filters and possible reduce of returned keys for each entity.

## Changes
Changes are a little bit complicated. Mongo has many options how update can happen which had to be reduced also it would be at this stage complicated to validate values which are created or updated thus automation is at this point almost none. Changes can be made using operations available in `~/client/operations.py`. Each operation require project name and entity type, but may require operation specific data.

### Create
Create operations expect already prepared document data, for that are prepared functions creating skeletal structures of documents (do not fill all required data), except `_id` all data should be right. Existence of entity is not validated so if the same creation operation is send n times it will create the entity n times which can cause issues.

### Update
Update operation require entity id and keys that should be changed, update dictionary must have {"key": value}. If value should be set in nested dictionary the key must have also all subkeys joined with dot `.` (e.g. `{"data": {"fps": 25}}` -> `{"data.fps": 25}`). To simplify update dictionaries were prepared functions which does that for you, their name has template `prepare_<entity type>_update_data` - they work on comparison of previous document and new document. If there is missing function for requested entity type it is because we didn't need it yet and require implementation.

### Delete
Delete operation need entity id. Entity will be deleted from mongo.


## What (probably) won't be replaced
Some parts of code are still using direct mongo calls. In most of cases it is for very specific calls that are module specific or their usage will completely change in future.
- Mongo calls that are not project specific (out of `avalon` collection) will be removed or will have to use different mechanism how the data are stored. At this moment it is related to OpenPype settings and logs, ftrack server events, some other data.
- Sync server queries. They're complex and very specific for sync server module. Their replacement will require specific calls to OpenPype server in v4 thus their abstraction with wrapper is irrelevant and would complicate production in v3.
- Project managers (ftrack, kitsu, shotgrid, embedded Project Manager, etc.). Project managers are creating, updating or removing assets in v3, but in v4 will create folders with different structure. Wrapping creation of assets would not help to prepare for v4 because of new data structures. The same can be said about editorial Extract Hierarchy Avalon plugin which create project structure.
- Code parts that is marked as deprecated in v3 or will be deprecated in v4.
    - integrate asset legacy publish plugin - already is legacy kept for safety
    - integrate thumbnail - thumbnails will be stored in different way in v4
    - input links - link will be stored in different way and will have different mechanism of linking. In v3 are links limited to same entity type "asset <-> asset" or "representation <-> representation".

## Known missing replacements
- change subset group in loader tool
- integrate subset group
- query input links in openpype lib
- create project in openpype lib
- save/create workfile doc in openpype lib
- integrate hero version
