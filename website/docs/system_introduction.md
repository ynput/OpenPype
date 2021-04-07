---
id: system_introduction
title: Introduction
sidebar_label: Introduction
---


**OpenPype** is a python application built on top of many other open-source libraries, modules and projects.
To be able to use it, you need those tools and set your environment. This
requires additional software installed and set up correctly on your system.

Fortunately this daunting task is mostly handled for you by OpenPype build and install scripts. **OpenPype** can
install most of its requirements automatically but a few more things are needed in
various usage scenarios.

## Studio Preparation

You can find detailed breakdown of technical requirements [here](dev_requirements), but in general OpenPype should be able
to operate in most studios fairly quickly. The main obstacles are usually related to workflows and habits, that
might now be fully compatible with what OpenPype is expecting or enforcing. 

Keep in mind that if you run into any workflows that are not supported, it's usually just because we haven't hit 
that particular case and it can most likely be added upon request. 


## Artist Workstations

To use **OpenPype** in production, it should be installed on each artist workstation, whether that is in the studio or at home in 
case of a distributed workflow. Once started, it lives in the system tray menu bar and all of it's tools are executed locally on 
the artist computer. There are no special requirements for the artist workstations if you are running openPype from a frozen build.

Each artist computer will need to be able to connect to your central mongo database to load and publish any work. They will also need
access to your centralized project storage, unless you are running a fully distributed pipeline.

## Centralized and Distributed?

OpenPype supports a variety of studio setups, for example:

- Single physical location with monolithic project storage.
- Fully remote studios, utilizing artist's home workstations.
- Distributed studios, running fully or partially on the cloud.
- Hybrid setups with different storages per project.
- And others that we probably didn't think of at all.

It is totally up to you how you deploy and distribute OpenPype to your artist, but there are a few things to keep in mind:
- While it is possible to store project files in different locations for different artist, it bring a lot of extra complexity
to the table
- Some DCCs do not support using Environment variables in file paths. This will make it very hard to maintain full multiplatform
compatibility as well variable storage roots.
- Relying on VPN connection and using it to work directly of network storage will be painfully slow.


## Repositories

### [OpenPype](https://github.com/pypeclub/pype)

This is where vast majority of the code that works with your data lives. It acts
as Avalon-Config, if we're speaking in avalon terms. 

Avalon gives us the ability to work with a certain host, say Maya, in a standardized manner, but OpenPype defines **how** we work with all the data, allows most of the behavior to be configured on a very granular level and provides a comprehensive build and installation tools for it.

Thanks to that, we are able to maintain one codebase for vast majority of the features across all our clients deployments while keeping the option to tailor the pipeline to each individual studio.

### [Avalon-core](https://github.com/pypeclub/avalon-core)

Avalon-core is the heart of OpenPype. It provides the base functionality including key GUIs (albeit expanded and modified by us), database connection, standards for data structures, working with entities and some universal tools.

Avalon is being actively developed and maintained by a community of studios and TDs from around the world, with Pype Club team being an active contributor as well.

Due to the extensive work we've done on OpenPype and the need to react quickly to production needs, we
maintain our own fork of avalon-core, which is kept up to date with upstream changes as much as possible.
