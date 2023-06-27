# OpenPype addon for AYON server
Convert openpype into AYON addon which can be installed on AYON server. The versioning of the addon is following versioning of OpenPype.

## Intro
As you might know, OpenPype is becoming AYON, which is moving from MongoDB to dedicated server with database. For some time, we'll keep OpenPype compatible with both MongoDB and AYON. But over time we'll start to change codebase to match AYON data and separate individual parts to addons.

At this moment have OpenPype codebase AYON mode, which means that OpenPype is using AYON server instead of MongoDB by under-laying conversion utils. At first, we added AYON executable next to OpenPype executables to start in AYON mode. That works, but would be hard to update new versions of code (would require new full installed build). We've decided to rather create new repository where is only base desktop application logic, for now we call it AYON launcher which will replace executables created by OpenPype build, and convert openpype code to server addon which reduce size of updates.

Because the overall implementation of ayon-launcher is not fully finished yet, we'll keep both ways how to start AYON mode for some time. Once the AYON launcher is finished, we'll remove AYON executables from OpenPype codebase completely.

For some time this addon will be requirement as an entry point to use AYON launcher.

## How to start
There is a `create_ayon_addon.py` python file which contains logic how to create server addon from OpenPype codebase. Just run the code.
```shell
./.poetry/bin/poetry run python ./server_addon/create_ayon_addon.py
```

It will create directory `./package/openpype/<OpenPype version>/*` folder with all files necessary for AYON server. You can then copy `./package/openpype/` to server addons, or zip the folder and upload it to AYON server. Restart server to update addons information, add the addon version to server bundle and set the bundle for production or staging usage.

Once addon is on server and is enabled, you can just run AYON launcher. Content will be downloaded and used automatically.
