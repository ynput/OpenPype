---
id: admin_getting_started
title: Getting Started
sidebar_label: Getting Started
---

## Introduction

**Pype** is part of a larger ecosystem of tools build around [avalon](https://github.com/getavalon/core) and [pyblish](https://github.com/pyblish/pyblish-base).
To be able to use it, you need those tools and set your environment. This
requires additional software installed and set up correctly on your system.

Fortunately this daunting task is handled for you by **Pype Setup** package itself. **Pype** can
install most of its requirements automatically but a few more things are needed in
various usage scenarios.

## Software requirements

- **Python 3.7+** (Locally on all workstations)
- **PowerShell 5.0+** (Windows only)
- **Bash** (Linux only)
- **MongoDB** (Centrally accessible)

There are other requirements for different advanced scenarios. For more
complete guide please refer to [Pype Setup page](admin_install).


## Hardware requirements

Pype should be installed centrally on a fast network storage with at least read access right for all workstations and users in the Studio. Full Deplyoyment with all dependencies and both Development and Production branches installed takes about 1GB of data, however to ensure smooth updates and general working comfort, we recommend allocating at least at least 4GB of storage dedicated to PYPE deployment.

For well functioning ftrack event server, we recommend a linux virtual server with Ubuntu or Centos OS. CPU and RAM allocation need differ based on the studio size, but a 2GB of ram, with a dual core CPU and around 4GB of storage should suffice

## Central repositories

### Pype-setup

Pype-Setup is the glue that binds Avalon, Pype and the Studio together. It is essentially a wrapper application that manages requirements, installation, all the environments and runs all of our standalone tools.

It has two main interfaces. `Pype` CLI command for all admin level tasks and a `Pype Tray` application for artists. Documentation for the `Pype` command can be found [here](admin_pype_commands)

This is also the only repository that needs to be downloaded by hand before full pype deployment can take place.

### Pype

Pype is our "Avalon Config" in Avalon terms that takes avalon-core and expands on it's default features and capabilities. This is where vast majority of the code that works with your data lives.

Avalon gives us the ability to work with a certain host, say Maya, in a standardised manner, but Pype defines **how** we work with all the data. You can think of it as. Avalon by default expects each studio to have their own avalon config, which is reasonable considering all studios have slightly different requirements and workflows. We abstracted a lot of this customisability out of the avalon config by allowing pype behaviour to be altered by a set of .json based configuration files and presets.

Thanks to that, we are able to maintain one codebase for vast majority of the features across all our clients deployments while keeping the option to tailor the pipeline to each individual studio.

### Avalon-core

Avalon-core is the heart and soul of Pype. It provides the base functionality including GUIs (albeit expanded modified by us), database connection and maintenance, standards for data structures and working with entities and a lot of universal tools.

Avalon is being very actively developed and maintained by a community of studios and TDs from around the world, with Pype Club team being an active contributor as well.

## Studio Specific Repositories

### Pype-Config

Pype_config repository need to be prepared and maintained for each studio using pype and holds all of their specific requiremens for pype. Those range from naming conventions and folder structures (in pype referred to as `project anatomy`), through colour management, data preferences, all the way to what individual  validators they want to use and what they are validating against.

Thanks to a very flexible and extensible system of presets, we're almost always able to accommodate client requests for modified behaviour by introducing new presets, rather than permanently altering the main codebase for everyone.


### Studio-Project-Configs

On top of studio wide pype config, we support project level overrides for any and all variables and presets available in the main studio config.

### Studio-Project-Scrips
