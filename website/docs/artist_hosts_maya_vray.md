---
id: artist_hosts_maya_vray
title: VRay for Maya
sidebar_label: VRay
---

## Working with VRay in OpenPype

### #Using VRay Proxies

OpenPype support publishing, loading and using of VRay Proxy in look management. Their underlying format
can be either vrmesh or alembic.

:::warning vrmesh or alembic and look management
Be aware that **vrmesh** cannot be used with looks as it doesn't retain IDs necessary to map shaders to geometry.
:::

### Creating VRay Proxy

To create VRay Proxy, select geometry you want and - **OpenPype → Create ...** select **VRay Proxy**. Name your
subset as you want and press **Create** button.

This will create `vrayproxy` set for your subset. You can set some options in Attribute editor, mainly if you want
export animation instead of single frame.

![Maya - VRay Proxy Creation](assets/maya-vray_proxy.jpg)

### Publishing VRay Proxies

VRay Proxy can be published - **OpenPype → Publish ...**. It will publish data as VRays `vrmesh` format and as
Alembic file.

## Using VRay Proxies

You can load VRay Proxy using loader - **OpenPype → Loader ...**

![Maya - VRay Proxy Creation](assets/maya-vray_proxy-loader.jpg)

Select your subset and right-click. Select **Import VRay Proxy (vrmesh)** to import it.

:::note
Note that even if it states `vrmesh` in descriptions, if loader finds Alembic published along (default behavior) it will
use abc file instead of vrmesh as it is more flexible and without it looks doesn't work.
:::
