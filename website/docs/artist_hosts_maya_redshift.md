---
id: artist_hosts_maya_redshift
title: Redshift for Maya
sidebar_label: Redshift
---

## Working with Redshift in OpenPype

### Using Redshift Proxies

OpenPype supports working with Redshift Proxy files. You can create  Redshift Proxy from almost
any hierarchy in Maya and it will be included there. Redshift can export animation
proxy file per frame.

### Creating Redshift Proxy

To mark data to publish as Redshift Proxy, select them in Maya and - **OpenPype → Create ...** and
then select **Redshift Proxy**. You can name your subset and hit **Create** button.

You can enable animation in Attribute Editor:

![Maya - Yeti Rig Setup](assets/maya-create_rs_proxy.jpg)

### Publishing Redshift Proxies

Once data are marked as Redshift Proxy instance, they can be published - **OpenPype → Publish ...**

### Using Redshift Proxies

Published proxy files can be loaded with OpenPype Loader. It will create mesh and attach Redshift Proxy
parameters to it - Redshift will then represent proxy with bounding box.
