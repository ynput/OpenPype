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

You can find a detailed breakdown of technical requirements [here](dev_requirements), but in general OpenPype should be able
to operate in most studios fairly quickly. The main obstacles are usually related to workflows and habits, that
might not be fully compatible with what OpenPype is expecting or enforcing. It is recommended to go through artists [key concepts](artist_concepts) to get comfortable with the basics.

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
