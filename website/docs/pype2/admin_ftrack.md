---
id: admin_ftrack
title: Ftrack Setup
sidebar_label: Ftrack Setup
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';


Ftrack is currently the main project management option for Pype. This documentation assumes that you are familiar with Ftrack and it's basic principles. If you're new to Ftrack, we recommend having a thorough look at [Ftrack Official Documentation](http://ftrack.rtd.ftrack.com/en/stable/).

## Prepare Ftrack for Pype

If you want to connect Ftrack to Pype you might need to make few changes in Ftrack settings. These changes would take a long time to do manually, so we prepared a few Ftrack actions to help you out. First, you'll need to launch Pype's tray application and set [Ftrack credentials](#credentials) to be able to run our Ftrack actions.

The only action that is strictly required is [Pype Admin - Create/Update Avalon Attributes](manager_ftrack_actions#create-update-avalon-attributes), which creates and sets the Custom Attributes necessary needed for Pype to function. If you want to use pype only for new projects then you should read about best practice with [new project](#new-project).

If you want to switch projects that are already in production, you might also need to run [Pype Doctor - Custom attr doc](manager_ftrack_actions#custom-attr-doc).

:::caution
Keep in mind that **Custom attr doc** action will migrate certain attributes from ftrack default ones to our custom attributes. Some attributes will also be renamed. We make backup of the values, but be very careful with this option and consults us before running it.
:::

## Event Server

Ftrack Event Server is the key to automation of many tasks like _status change_, _thumbnail update_, _automatic synchronization to Avalon database_ and many more. Event server should run at all times to perform all the required processing as it is not possible to catch some of them retrospectively with enough certainty.

### Running event server

There are specific launch arguments for event server. With `$PYPE_SETUP/pype eventserver` you can launch event server but without prior preparation it will terminate immediately. The reason is that event server requires 3 pieces of information: _Ftrack server url_, _paths to events_ and _Credentials (Username and API key)_. Ftrack server URL and Event path are set from Pype's environments by default, but the credentials must be done separatelly for security reasons.



:::note There are 2 ways of passing your credentials to event server.

<Tabs
  defaultValue="args"
  values={[
    {label: 'Additional Arguments', value: 'args'},
    {label: 'Environments Variables', value: 'env'}
  ]}>

<TabItem value="args">

-  **`--ftrack-user "your.username"`** : Ftrack Username
-   **`--ftrack-api-key "00000aaa-11bb-22cc-33dd-444444eeeee"`** : User's API key
-   **`--store-crededentials`** : Entered credentials will be stored for next launch with this argument _(It is not needed to enter **ftrackuser** and **ftrackapikey** args on next launch)_
-   **`--no-stored-credentials`** : Stored credentials are loaded first so if you want to change credentials use this argument
-   `--ftrack-url "https://yourdomain.ftrackapp.com/"` : Ftrack server URL _(it is not needed to enter if you have set `FTRACK_SERVER` in Pype' environments)_
-   `--ftrack-events-path "//Paths/To/Events/"` : Paths to events folder. May contain multiple paths separated by `;`. _(it is not needed to enter if you have set `FTRACK_EVENTS_PATH` in Pype' environments)_

So if you want to use Pype's environments then you can launch event server for first time with these arguments `$PYPE_SETUP/pype eventserver --ftrack-user "my.username" --ftrack-api-key "00000aaa-11bb-22cc-33dd-444444eeeee" --store-credentials`. Since that time, if everything was entered correctly, you can launch event server with `$PYPE_SETUP/pype eventserver`.

</TabItem>
<TabItem value="env">

- `FTRACK_API_USER` - Username _("your.username")_
- `FTRACK_API_KEY` - User's API key _("00000aaa-11bb-22cc-33dd-444444eeeee")_
- `FTRACK_SERVER` - Ftrack server url _("<https://yourdomain.ftrackapp.com/">)_
- `FTRACK_EVENTS_PATH` - Paths to events _("//Paths/To/Events/")_
    We do not recommend you this way.

</TabItem>
</Tabs>
:::

:::caution
We do not recommend setting your ftrack user and api key environments in a persistent way, for security reasons. Option 1. passing them as arguments is substantially safer.
:::

### Where to run event server

We recommend you to run event server on stable server machine with ability to connect to Avalon database and Ftrack web server. Best practice we recommend is to run event server as service.

:::important
Event server should **not** run more than once! It may cause big pipeline issues.
:::

### Which user to use

-   must have at least `Administrator` role
-   same user should not be used by an artist

### Run Linux service - step by step

1.  create file:
    `sudo vi /opt/pype/run_event_server.sh`

2.  add content to the file:

```sh
export PYPE_DEBUG=3
pushd /mnt/pipeline/prod/pype-setup
. pype eventserver --ftrack-user <pype-admin-user> --ftrack-api-key <api-key>
```

3.  create service file:
    `sudo vi /etc/systemd/system/pype-ftrack-event-server.service`

4.  add content to the service file

```toml
[Unit]
Description=Run Pype Ftrack Event Server Service
After=network.target

[Service]
Type=idle
ExecStart=/opt/pype/run_event_server.sh
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

5.  change file permission:
    `sudo chmod 0755 /etc/systemd/system/pype-ftrack-event-server.service`

6.  enable service:
    `sudo systemctl enable pype-ftrack-event-server`

7.  start service:
    `sudo systemctl start pype-ftrack-event-server`

* * *

## Ftrack events

Events are helpers to automation. They react to Ftrack Web Server events like change entity attribute, create of entity, etc. .

### Delete Avalon ID from new entity _(DelAvalonIdFromNew)_

Is used to remove value from `Avalon/Mongo Id` Custom Attribute when entity is created.

`Avalon/Mongo Id` Custom Attribute stores id of synchronized entities in pipeline database. When user _Copy -> Paste_ selection of entities to create similar hierarchy entities, values from Custom Attributes are copied too. That causes issues during synchronization because there are multiple entities with same value of `Avalon/Mongo Id`. To avoid this error we preventively remove these values when entity is created.

### Next Task update _(NextTaskUpdate)_

Change status of next task from `Not started` to `Ready` when previous task is approved.

Multiple detailed rules for next task update can be configured in the presets.

### Synchronization to Avalon database _(Sync_to_Avalon)_

Automatic [synchronization to pipeline database](manager_ftrack#synchronization-to-avalon-database).

This event updates entities on their changes Ftrack. When new entity is created or existing entity is modified. Interface with listing information is shown to users when [synchronization rules](manager_ftrack#synchronization-rules) are not met. This event may also undo changes when they might break pipeline. Namely _change name of synchronized entity_, _move synchronized entity in hierarchy_.

:::important
Deleting an entity by Ftrack's default is not processed for security reasons _(to delete entity use [Delete Asset/Subset action](manager_ftrack_actions#delete-asset-subset))_.
:::

### Synchronize hierarchical attributes _(SyncHierarchicalAttrs)_

Auto-synchronization of hierarchical attributes from Ftrack entities.

Related to [Synchronize to Avalon database](#synchronization-to-avalon-database) event _(without it, it makes no sense to use this event)_. Hierarchical attributes must be synchronized with special way so we needed to split synchronization into 2 parts. There are [synchronization rules](manager_ftrack#synchronization-rules) for hierarchical attributes that must be met otherwise interface with messages about not meeting conditions is shown to user.

### Thumbnails update _(ThumbnailEvents)_

Updates thumbnail of Task and it's parent when new Asset Version with thumbnail is created.

This is normally done by Ftrack Web server when Asset Version is created with Drag&Drop but not when created with Ftrack API.

### Version to Task status _(VersionToTaskStatus)_

Updates Task status based on status changes on it's `AssetVersion`.

The issue this solves is when Asset version's status is changed but the artist assigned to Task is looking at the task status, thus not noticing the review.

This event makes sure statuses Asset Version get synced to it's task. After changing a status on version, this event first tries to set identical status to version's parent (usually task). At this moment there are a few more status mappings hardcoded into the system. If Asset version's status was changed to:

-   `Reviewed` then Task's status will be changed to `Change requested`
-   `Approved` then Task's status will be changed to `Complete`


### Update First Version status _(FirstVersionStatus)_

This event handler allows setting of different status to a first created Asset Version in ftrack.

This is useful for example if first version publish doesn't contain any actual reviewable work, but is only used for roundtrip conform check, in which case this version could receive status `pending conform` instead of standard `pending review`

Behaviour can be filtered by `name` or `type` of the task assigned to the Asset Version. Configuration can be found in [ftrack presets](admin_presets_ftrack#first_version_status-dict)

* * *

## Credentials

If you want to be able use Ftrack actions with Pype tray or [event server](#event-server) you need to enter credentials. The credentials required for Ftrack are `Username` and `API key`.

### Credentials in tray

How to handle with credentials in tray is described [here](#artist_ftrack#first-use-best-case-scenario).

### Credentials in event server

How to enter credentials to event server is described [here](#how-to-run-event-server).

### Where to find API key

Please check the [official documentation](http://ftrack.rtd.ftrack.com/en/backlog-scaling-ftrack-documentation-story/developing/api_keys.html).
