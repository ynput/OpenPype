---
title: Getting started with Pype
sidebar_label: Getting started
---


## Basic use

If you have Pype installed and deployed, you can start using it. Ideally you should
have Pype icon on your desktop or even have your computer set up so Pype will start
automatically.

Otherwise for most common stuff there are so-called *launchers* - scripts you can just run from desktop shortcut or
whatever and you are done. There is also manual invocation of Pype command you can use
for slightly more control.

:::tip Launchers
Launchers can be found in `pype/launchers` directory. They are basically shell scripts running Pype. You can create shortcuts on desktop for them for easy Pype launching.
:::

### Starting tray manually

**Pype Tray** is most common Pype command for artists. It runs Pype GUI in system tray
from which you can work with Pype. To use Pype, **Pype Tray** must be running.

To run **Pype Tray**:

```sh
pype tray
```

or run launcher `launchers/pype_tray.bat` (Windows) or `launchers/pype_tray.sh` (Linux)

:::note Debugging
To get more information on what's going on in Pype, you can run Tray with `--debug` option. This will show text console window with lots of useful information.
```sh
pype tray --debug
```
:::

### Advanced use

For more advanced use of Pype command please visit [Admin section](admin_pype_commands).
