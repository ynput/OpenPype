---
id: module_kitsu
title: Kitsu Administration
sidebar_label: Kitsu
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

Kitsu is a great open source production tracker and can be used for project management instead of Ftrack. This documentation assumes that you are familiar with Kitsu and it's basic principles. If you're new to Kitsu, we recommend having a thorough look at [Kitsu Official Documentation](https://kitsu.cg-wire.com/).

## Prepare Kitsu for OpenPype

### Server URL
If you want to connect Kitsu to OpenPype you have to set the `Server` url in Kitsu settings. And that's all!
This setting is available for all the users of the OpenPype instance.

## Synchronize
Updating OP with Kitsu data is executed running the `sync-service`, which requires to provide your Kitsu credentials with `-l, --login` and `-p, --password` or by setting the environment variables `KITSU_LOGIN` and `KITSU_PWD`. This process will request data from Kitsu and create/delete/update OP assets.
Once this sync is done, the thread will automatically start a loop to listen to Kitsu events.

```bash
openpype_console module kitsu sync-service -l me@domain.ext -p my_password
```

### Events listening
Listening to Kitsu events is the key to automation of many tasks like _project/episode/sequence/shot/asset/task create/update/delete_ and some more. Events listening should run at all times to perform the required processing as it is not possible to catch some of them retrospectively with strong reliability. If such timeout has been encountered, you must relaunch the `sync-service` command to run the synchronization step again.

### Push to Kitsu
An utility function is provided to help update Kitsu data (a.k.a Zou database) with OpenPype data if the publishing to the production tracker hasn't been possible for some time. Running `push-to-zou` will create the data on behalf of the user.
:::caution
This functionality cannot deal with all cases and is not error proof, some intervention by a human being might be required.
:::

```bash
openpype_console module kitsu push-to-zou -l me@domain.ext -p my_password
```
