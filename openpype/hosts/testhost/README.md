# What is `testhost`
Host `testhost` was created to fake running host for testing of publisher.

Does not have any proper launch mechanism at the moment. There is python script `./run_publish.py` which will show publisher window. The script requires to set few variables to run. Execution will register host `testhost`, register global publish plugins and register creator and publish plugins from `./plugins`.

## Data
Created instances and context data are stored into json files inside `./api` folder. Can be easily modified to save them to a different place.

## Plugins
Test host has few plugins to be able test publishing.

### Creators
They are just example plugins using functions from `api` to create/remove/update data. One of them is auto creator which means that is triggered on each reset of create context. Others are manual creators both creating the same family.

### Publishers
Collectors are example plugin to use `get_attribute_defs` to define attributes for specific families or for context. Validators are to test `PublishValidationError`.
