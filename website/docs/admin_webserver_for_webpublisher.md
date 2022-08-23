---
id: admin_webserver_for_webpublisher
title: Webserver for webpublisher
sidebar_label: Webserver for webpublisher
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

Running Openpype webserver is needed as a backend part for Web publishing. 
Any OS supported by Openpype could be used as a host server.

Webpublishing consists of two sides, Front end (FE) and Openpype backend. This documentation is only targeted on OP side.

It is expected that FE and OP will live on two separate servers, FE publicly available, OP safely in customer network.

# Requirements for servers
- OP server allows access to its `8079` port for FE. (It is recommended to whitelist only FE IP.)
- have shared folder for published resources (images, workfiles etc) on both servers

# Prepare Ftrack
Current webpublish process expects authentication via Slack. It is expected that customer has users created on a Ftrack
with same email addresses as on Slack. As some customer might have usernames different from emails, conversion from email to username is needed.

For this "pype.club" user needs to be present on Ftrack, creation of this user should be standard part of Ftrack preparation for Openpype.
Next create API key on Ftrack, store this information temporarily as you won't have access to this key after creation.


# Prepare Openpype

Deploy OP build distribution (Openpype Igniter) on an OS of your choice.

##Run webserver as a Linux service:

(This expects that OP Igniter is deployed to `opt/openpype` and log should be stored in `/tmp/openpype.log`)

- create file `sudo vi /opt/openpype/webpublisher_webserver.sh`

- paste content
```sh
#!/usr/bin/env bash
export OPENPYPE_DEBUG=3
export FTRACK_BOT_API_USER=YOUR_API_USER
export FTRACK_BOT_API_KEY=YOUR_API_KEY
export PYTHONDONTWRITEBYTECODE=1
export OPENPYPE_MONGO=YOUR_MONGODB_CONNECTION

pushd /opt/openpype
./openpype_console webpublisherwebserver --upload_dir YOUR_SHARED_FOLDER_ON_HOST  --executable /opt/openpype/openpype_console  --host YOUR_HOST_IP --port YOUR_HOST_PORT > /tmp/openpype.log 2>&1
```

1. create service file `sudo vi /etc/systemd/system/openpye-webserver.service`

2. paste content
```sh
[Unit]
Description=Run OpenPype Ftrack Webserver Service
After=network.target

[Service]
Type=idle
ExecStart=/opt/openpype/webpublisher_webserver.sh
Restart=on-failure
RestartSec=10s
StandardOutput=append:/tmp/openpype.log
StandardError=append:/tmp/openpype.log

[Install]
WantedBy=multi-user.target
```

5.  change file permission:
    `sudo chmod 0755 /etc/systemd/system/openpype-webserver.service`

6.  enable service:
    `sudo systemctl enable openpype-webserver`

7.  start service:
    `sudo systemctl start openpype-webserver`
    
8. Check `/tmp/openpype.log` if OP got started

(Note: service could be restarted by `service openpype-webserver restart` - this will result in purge of current log file!)